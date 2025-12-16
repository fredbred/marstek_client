"""Script to discover Marstek batteries on the local network using UDP broadcast."""

import asyncio
import json
import socket
import sys
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def discover_batteries(timeout: float = 5.0) -> list[dict[str, Any]]:
    """Discover Marstek batteries on the local network.

    Args:
        timeout: Timeout for discovery in seconds

    Returns:
        List of discovered batteries with their information
    """
    discovered: list[dict[str, Any]] = []

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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

        # Send broadcast
        broadcast_address = ("255.255.255.255", 30000)
        logger.info("sending_discovery_broadcast", address=broadcast_address)
        sock.sendto(request_bytes, broadcast_address)

        # Listen for responses
        logger.info("listening_for_responses", timeout=timeout)

        while True:
            try:
                response_data, addr = sock.recvfrom(4096)
                response_json = response_data.decode("utf-8")
                response = json.loads(response_json)

                # Check if it's a valid response
                if "result" in response and "device" in response["result"]:
                    device_info = response["result"]
                    battery_info = {
                        "device": device_info.get("device"),
                        "version": device_info.get("ver"),
                        "ip": device_info.get("ip"),
                        "wifi_mac": device_info.get("wifi_mac"),
                        "ble_mac": device_info.get("ble_mac"),
                        "wifi_name": device_info.get("wifi_name"),
                        "source": response.get("src"),
                    }

                    discovered.append(battery_info)
                    logger.info("battery_discovered", **battery_info)

            except socket.timeout:
                break
            except json.JSONDecodeError as e:
                logger.warning("invalid_json_response", error=str(e), data=response_data[:100])
            except Exception as e:
                logger.error("error_processing_response", error=str(e))

    except Exception as e:
        logger.error("discovery_error", error=str(e))
    finally:
        sock.close()

    return discovered


def print_results(batteries: list[dict[str, Any]]) -> None:
    """Print discovered batteries in a formatted way.

    Args:
        batteries: List of discovered batteries
    """
    if not batteries:
        print("\n❌ No batteries discovered.")
        print("\nMake sure:")
        print("  - Batteries are powered on and connected to the network")
        print("  - Open API is enabled in the Marstek app")
        print("  - You are on the same network as the batteries")
        return

    print(f"\n✅ Discovered {len(batteries)} battery(ies):\n")

    for idx, battery in enumerate(batteries, 1):
        print(f"Battery {idx}:")
        print(f"  Device: {battery.get('device', 'Unknown')}")
        print(f"  IP: {battery.get('ip', 'Unknown')}")
        print(f"  Version: {battery.get('version', 'Unknown')}")
        print(f"  WiFi MAC: {battery.get('wifi_mac', 'Unknown')}")
        print(f"  BLE MAC: {battery.get('ble_mac', 'Unknown')}")
        print(f"  WiFi Name: {battery.get('wifi_name', 'Unknown')}")
        print()


async def main() -> None:
    """Main entry point."""
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    )

    print("🔍 Discovering Marstek batteries on local network...\n")

    batteries = await discover_batteries(timeout=5.0)

    print_results(batteries)

    # Generate config snippet
    if batteries:
        print("\n📋 Configuration snippet for .env:")
        print("\n# Batteries")
        for idx, battery in enumerate(batteries, 1):
            ip = battery.get("ip", f"192.168.1.{100 + idx}")
            port = 30000 + idx
            print(f"BATTERY_{idx}_IP={ip}")
            print(f"BATTERY_{idx}_PORT={port}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Discovery interrupted by user")
        sys.exit(0)

