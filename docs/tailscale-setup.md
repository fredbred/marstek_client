# Configuration Tailscale (Alternative VPN)

Guide pour configurer Tailscale comme alternative à Cloudflare Tunnel.

## 🎯 Pourquoi Tailscale ?

- ✅ Pas besoin de domaine
- ✅ Configuration automatique
- ✅ Chiffrement end-to-end
- ✅ Gratuit (jusqu'à 100 appareils)

## 📦 Installation

### Sur Raspberry Pi / Linux
\`\`\`bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
\`\`\`

### Sur Windows / macOS / Mobile
Télécharger depuis [tailscale.com/download](https://tailscale.com/download)

## ⚙️ Configuration

1. Créer un compte sur [tailscale.com](https://tailscale.com)
2. Se connecter sur tous vos appareils
3. Accéder via les IPs Tailscale :
   - Streamlit: `http://<RASPBERRY_IP>:8501`
   - API: `http://<RASPBERRY_IP>:8000`

## 🔒 Sécurité

- Utiliser l'authentification à deux facteurs
- Surveiller les appareils connectés
- Configurer des ACLs si nécessaire

## 🔍 Dépannage

\`\`\`bash
# Vérifier le statut
sudo systemctl status tailscaled
tailscale status

# Redémarrer
sudo systemctl restart tailscaled
\`\`\`

## 📚 Ressources

- [Documentation Tailscale](https://tailscale.com/kb/)
