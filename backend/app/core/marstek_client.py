"""UDP client for Marstek devices using JSON-RPC protocol.

Implements the Marstek Device Open API protocol over UDP according to
MarstekDeviceOpenApi.pdf specification.
"""

import asyncio
import json
import socket
from typing import Any

import structlog

from app.models.marstek_api import (
    BatteryStatus,
    DeviceInfo,
    ESStatus,
    ManualConfig,
    ModeInfo,
    SetModeResult,
)

logger = structlog.get_logger(__name__)


class MarstekAPIError(Exception):
    """Custom exception for Marstek API errors."""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        method: str | None = None,
        response: dict[str, Any] | None = None,
    ) -> None:
        """Initialize Marstek API error.

        Args:
            message: Error message
            code: JSON-RPC error code
            method: Method that failed
            response: Full error response
        """
        super().__init__(message)
        self.code = code
        self.method = method
        self.response = response


class MarstekUDPClient:
    """UDP client for communicating with Marstek devices using JSON-RPC.

    Implements the Marstek Device Open API protocol over UDP.
    """

    def __init__(
        self,
        timeout: float = 5.0,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
        instance_id: int = 0,
    ) -> None:
        """Initialize Marstek UDP client.

        Args:
            timeout: Timeout for UDP requests in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff: Base backoff time in seconds (exponential)
            instance_id: Default instance ID for device commands
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.instance_id = instance_id
        self._request_id = 0
        self._socket: socket.socket | None = None

    def _get_next_request_id(self) -> int:
        """Get next request ID for JSON-RPC."""
        self._request_id += 1
        return self._request_id

    async def _create_socket(self) -> socket.socket:
        """Create and configure UDP socket."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        return sock

    async def send_command(
        self, ip: str, port: int, command_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """Send JSON-RPC command to device with retry logic.

        Args:
            ip: Device IP address
            port: Device UDP port
            command_dict: JSON-RPC command dictionary

        Returns:
            JSON-RPC response dictionary

        Raises:
            MarstekAPIError: If command fails after all retries
            TimeoutError: If request times out
            ConnectionError: If network error occurs
        """
        request_id = self._get_next_request_id()
        command_dict["id"] = request_id

        request_json = json.dumps(command_dict)
        request_bytes = request_json.encode("utf-8")

        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            sock = await self._create_socket()

            try:
                # Send request
                sock.sendto(request_bytes, (ip, port))

                logger.debug(
                    "marstek_command_sent",
                    ip=ip,
                    port=port,
                    method=command_dict.get("method"),
                    request_id=request_id,
                    attempt=attempt,
                )

                # Wait for response
                response_data, addr = await asyncio.to_thread(sock.recvfrom, 4096)

                # Parse JSON response
                response_json = response_data.decode("utf-8")
                response = json.loads(response_json)

                # Verify response ID matches request
                if response.get("id") != request_id:
                    logger.warning(
                        "marstek_response_id_mismatch",
                        expected_id=request_id,
                        received_id=response.get("id"),
                        ip=ip,
                        port=port,
                    )
                    sock.close()
                    continue

                # Check for JSON-RPC error
                if "error" in response:
                    error = response["error"]
                    error_code = error.get("code")
                    error_message = error.get("message", "Unknown error")

                    logger.error(
                        "marstek_jsonrpc_error",
                        ip=ip,
                        port=port,
                        method=command_dict.get("method"),
                        error_code=error_code,
                        error_message=error_message,
                        attempt=attempt,
                    )

                    raise MarstekAPIError(
                        f"JSON-RPC error: {error_message} (code: {error_code})",
                        code=error_code,
                        method=command_dict.get("method"),
                        response=response,
                    )

                # Success
                logger.debug(
                    "marstek_command_success",
                    ip=ip,
                    port=port,
                    method=command_dict.get("method"),
                    attempt=attempt,
                )

                sock.close()
                return response

            except TimeoutError as e:
                last_error = e
                logger.warning(
                    "marstek_command_timeout",
                    ip=ip,
                    port=port,
                    method=command_dict.get("method"),
                    attempt=attempt,
                    max_retries=self.max_retries,
                )
                sock.close()

                if attempt < self.max_retries:
                    backoff_time = self.retry_backoff * (2 ** (attempt - 1))
                    await asyncio.sleep(backoff_time)

            except json.JSONDecodeError as e:
                last_error = e
                logger.error(
                    "marstek_json_decode_error",
                    ip=ip,
                    port=port,
                    method=command_dict.get("method"),
                    attempt=attempt,
                    error=str(e),
                    response_preview=(
                        response_data[:100] if "response_data" in locals() else None
                    ),
                )
                sock.close()

                if attempt < self.max_retries:
                    backoff_time = self.retry_backoff * (2 ** (attempt - 1))
                    await asyncio.sleep(backoff_time)

            except OSError as e:
                last_error = e
                logger.error(
                    "marstek_network_error",
                    ip=ip,
                    port=port,
                    method=command_dict.get("method"),
                    attempt=attempt,
                    error=str(e),
                )
                sock.close()

                if attempt < self.max_retries:
                    backoff_time = self.retry_backoff * (2 ** (attempt - 1))
                    await asyncio.sleep(backoff_time)

        # All retries failed
        logger.error(
            "marstek_command_failed",
            ip=ip,
            port=port,
            method=command_dict.get("method"),
            max_retries=self.max_retries,
            error=str(last_error) if last_error else "Unknown error",
        )

        if isinstance(last_error, socket.timeout):
            raise TimeoutError(
                f"Timeout sending command to {ip}:{port} after {self.max_retries} attempts"
            ) from last_error

        raise ConnectionError(
            f"Failed to send command to {ip}:{port} after {self.max_retries} attempts"
        ) from last_error

    async def broadcast_discover(
        self, timeout: float = 5.0, port: int = 30000
    ) -> list[DeviceInfo]:
        """Discover Marstek devices on local network via UDP broadcast.

        Args:
            timeout: Timeout for discovery in seconds
            port: UDP port to broadcast to (default: 30000)

        Returns:
            List of discovered devices
        """
        discovered: list[DeviceInfo] = []

        # Create broadcast socket
        sock = await self._create_socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)

        try:
            # Broadcast discovery request
            request = {
                "id": 0,
                "method": "Marstek.GetDevice",
                "params": {"ble_mac": "0"},
            }

            request_json = json.dumps(request)
            request_bytes = request_json.encode("utf-8")

            broadcast_address = ("255.255.255.255", port)

            logger.info("marstek_discovery_started", port=port, timeout=timeout)
            sock.sendto(request_bytes, broadcast_address)

            # Listen for responses
            while True:
                try:
                    response_data, addr = await asyncio.to_thread(sock.recvfrom, 4096)
                    response_json = response_data.decode("utf-8")
                    response = json.loads(response_json)

                    # Check if it's a valid device response
                    if "result" in response and "device" in response["result"]:
                        result = response["result"]
                        device_info = DeviceInfo(
                            device=result.get("device", ""),
                            ver=result.get("ver", 0),
                            ble_mac=result.get("ble_mac", ""),
                            wifi_mac=result.get("wifi_mac", ""),
                            wifi_name=result.get("wifi_name"),
                            ip=result.get("ip", ""),
                        )

                        discovered.append(device_info)

                        logger.info(
                            "marstek_device_discovered",
                            device=device_info.device,
                            ip=device_info.ip,
                            version=device_info.ver,
                        )

                except TimeoutError:
                    break
                except json.JSONDecodeError as e:
                    logger.warning("marstek_discovery_invalid_response", error=str(e))
                except Exception as e:
                    logger.error("marstek_discovery_error", error=str(e))

        except Exception as e:
            logger.error("marstek_discovery_failed", error=str(e))
        finally:
            sock.close()

        logger.info("marstek_discovery_complete", devices_found=len(discovered))
        return discovered

    async def get_device_info(
        self, ip: str, port: int, ble_mac: str = "0"
    ) -> DeviceInfo:
        """Get device information.

        Args:
            ip: Device IP address
            port: Device UDP port
            ble_mac: Bluetooth MAC address (use "0" for discovery)

        Returns:
            Device information

        Raises:
            MarstekAPIError: If command fails
        """
        command = {
            "method": "Marstek.GetDevice",
            "params": {"ble_mac": ble_mac},
        }

        response = await self.send_command(ip, port, command)

        if "result" not in response:
            raise MarstekAPIError(
                "No result in response", method="Marstek.GetDevice", response=response
            )

        result = response["result"]
        return DeviceInfo(
            device=result.get("device", ""),
            ver=result.get("ver", 0),
            ble_mac=result.get("ble_mac", ""),
            wifi_mac=result.get("wifi_mac", ""),
            wifi_name=result.get("wifi_name"),
            ip=result.get("ip", ""),
        )

    async def get_battery_status(
        self, ip: str, port: int, instance_id: int | None = None
    ) -> BatteryStatus:
        """Get battery status.

        Args:
            ip: Device IP address
            port: Device UDP port
            instance_id: Instance ID (default: self.instance_id)

        Returns:
            Battery status

        Raises:
            MarstekAPIError: If command fails
        """
        if instance_id is None:
            instance_id = self.instance_id

        command = {
            "method": "Bat.GetStatus",
            "params": {"id": instance_id},
        }

        response = await self.send_command(ip, port, command)

        if "result" not in response:
            raise MarstekAPIError(
                "No result in response", method="Bat.GetStatus", response=response
            )

        result = response["result"]

        # SOC can be string or number in API, convert to int
        soc = result.get("soc")
        if isinstance(soc, str):
            try:
                soc = int(soc)
            except ValueError:
                soc = 0
        elif soc is None:
            soc = 0

        return BatteryStatus(
            id=result.get("id", instance_id),
            soc=soc,
            charg_flag=result.get("charg_flag", False),
            dischrg_flag=result.get("dischrg_flag", False),
            bat_temp=result.get("bat_temp"),
            bat_capacity=result.get("bat_capacity"),
            rated_capacity=result.get("rated_capacity"),
        )

    async def get_es_status(
        self, ip: str, port: int, instance_id: int | None = None
    ) -> ESStatus:
        """Get Energy System status.

        Args:
            ip: Device IP address
            port: Device UDP port
            instance_id: Instance ID (default: self.instance_id)

        Returns:
            Energy System status

        Raises:
            MarstekAPIError: If command fails
        """
        if instance_id is None:
            instance_id = self.instance_id

        command = {
            "method": "ES.GetStatus",
            "params": {"id": instance_id},
        }

        response = await self.send_command(ip, port, command)

        if "result" not in response:
            raise MarstekAPIError(
                "No result in response", method="ES.GetStatus", response=response
            )

        result = response["result"]
        return ESStatus(**result)

    async def get_current_mode(
        self, ip: str, port: int, instance_id: int | None = None
    ) -> ModeInfo:
        """Get current device mode.

        Args:
            ip: Device IP address
            port: Device UDP port
            instance_id: Instance ID (default: self.instance_id)

        Returns:
            Mode information

        Raises:
            MarstekAPIError: If command fails
        """
        if instance_id is None:
            instance_id = self.instance_id

        command = {
            "method": "ES.GetMode",
            "params": {"id": instance_id},
        }

        response = await self.send_command(ip, port, command)

        if "result" not in response:
            raise MarstekAPIError(
                "No result in response", method="ES.GetMode", response=response
            )

        result = response["result"]

        # Mode can be string or number, convert to string
        mode = result.get("mode")
        if isinstance(mode, int):
            mode_map = {0: "Auto", 1: "AI", 2: "Manual", 3: "Passive"}
            mode = mode_map.get(mode, "Unknown")
        elif mode is None:
            mode = None

        return ModeInfo(
            id=result.get("id"),
            mode=mode,
            ongrid_power=result.get("ongrid_power"),
            offgrid_power=result.get("offgrid_power"),
            bat_soc=result.get("bat_soc"),
        )

    async def set_mode_auto(
        self, ip: str, port: int, instance_id: int | None = None
    ) -> bool:
        """Set device to Auto mode.

        Args:
            ip: Device IP address
            port: Device UDP port
            instance_id: Instance ID (default: self.instance_id)

        Returns:
            True if successful, False otherwise

        Raises:
            MarstekAPIError: If command fails
        """
        if instance_id is None:
            instance_id = self.instance_id

        command = {
            "method": "ES.SetMode",
            "params": {
                "id": instance_id,
                "config": {
                    "mode": "Auto",
                    "auto_cfg": {"enable": 1},
                },
            },
        }

        response = await self.send_command(ip, port, command)

        if "result" not in response:
            raise MarstekAPIError(
                "No result in response", method="ES.SetMode", response=response
            )

        result = SetModeResult(**response["result"])
        return result.set_result

    async def set_mode_manual(
        self, ip: str, port: int, config: ManualConfig, instance_id: int | None = None
    ) -> bool:
        """Set device to Manual mode.

        Args:
            ip: Device IP address
            port: Device UDP port
            config: Manual mode configuration
            instance_id: Instance ID (default: self.instance_id)

        Returns:
            True if successful, False otherwise

        Raises:
            MarstekAPIError: If command fails
        """
        if instance_id is None:
            instance_id = self.instance_id

        command = {
            "method": "ES.SetMode",
            "params": {
                "id": instance_id,
                "config": {
                    "mode": "Manual",
                    "manual_cfg": config.model_dump(),
                },
            },
        }

        response = await self.send_command(ip, port, command)

        if "result" not in response:
            raise MarstekAPIError(
                "No result in response", method="ES.SetMode", response=response
            )

        result = SetModeResult(**response["result"])
        return result.set_result
