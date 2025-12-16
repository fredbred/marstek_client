# Configuration Cloudflare Tunnel (Gratuit)

Guide complet pour configurer un accès distant sécurisé à l'application Marstek Automation via Cloudflare Tunnel.

## 📋 Table des matières

1. [Prérequis](#prérequis)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Sécurité](#sécurité)
5. [Alternative Tailscale](#alternative-tailscale)
6. [Dépannage](#dépannage)

## 🔧 Prérequis

### Compte Cloudflare
- Compte Cloudflare gratuit ([inscription](https://dash.cloudflare.com/sign-up))
- Domaine enregistré (peut être transféré gratuitement sur Cloudflare)

### Matériel
- Raspberry Pi ou serveur Linux avec accès root
- Connexion Internet stable
- Ports locaux 8000 (API) et 8501 (Streamlit) accessibles

## 📦 Installation

### 1. Installation de cloudflared

#### Sur Raspberry Pi (ARM64)
\`\`\`bash
# Télécharger la dernière version
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb

# Installer
sudo dpkg -i cloudflared-linux-arm64.deb

# Vérifier l'installation
cloudflared --version
\`\`\`

#### Sur Raspberry Pi (ARM32)
\`\`\`bash
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm
sudo mv cloudflared-linux-arm /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared
\`\`\`

### 2. Authentification Cloudflare

\`\`\`bash
# Se connecter à votre compte Cloudflare
cloudflared tunnel login

# Suivre les instructions pour autoriser l'accès
\`\`\`

### 3. Création du tunnel

\`\`\`bash
# Créer un nouveau tunnel
cloudflared tunnel create marstek-home

# Notez le Tunnel ID qui sera affiché
\`\`\`

### 4. Configuration DNS

\`\`\`bash
# Créer les enregistrements DNS
cloudflared tunnel route dns marstek-home marstek.<DOMAIN>
cloudflared tunnel route dns marstek-home api-marstek.<DOMAIN>
\`\`\`

## ⚙️ Configuration

### 1. Fichier de configuration

Créer le fichier `/etc/cloudflared/config.yml` (voir `cloudflared-config.yml.example`).

### 2. Service systemd

Créer le fichier `/etc/systemd/system/cloudflared.service` (voir `cloudflared.service.example`).

### 3. Activation et démarrage

\`\`\`bash
sudo systemctl daemon-reload
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
sudo systemctl status cloudflared
\`\`\`

## 🔒 Sécurité

### 1. Cloudflare Access (Authentification par email)

1. Aller dans **Zero Trust** > **Access** > **Applications**
2. Créer une application pour `marstek.ton-domaine.com`
3. Configurer une politique avec vos emails autorisés

### 2. Rate Limiting

Dans **Security** > **WAF** > **Rate limiting rules**, créer une règle pour limiter les requêtes.

### 3. WAF (Web Application Firewall)

Activer les règles **Managed rules** > **Cloudflare Managed Ruleset** et **OWASP Core Ruleset**.

### 4. Configuration SSL/TLS

Sélectionner **Full (strict)** pour le mode SSL dans **SSL/TLS** > **Overview**.

## 🚀 Alternative : Tailscale

Voir `tailscale-setup.md` pour une alternative VPN sans domaine requis.

## 🔍 Dépannage

### Le tunnel ne démarre pas
\`\`\`bash
sudo journalctl -u cloudflared -n 50
cloudflared tunnel --config /etc/cloudflared/config.yml run
\`\`\`

### Erreur "tunnel not found"
\`\`\`bash
cloudflared tunnel list
\`\`\`

## 📚 Ressources

- [Documentation Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Documentation Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/policies/access/)
