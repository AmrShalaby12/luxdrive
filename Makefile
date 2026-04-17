cert_esolve:
	        sudo certbot certonly  --dns-cloudflare --dns-cloudflare-credentials dns-credentials/ahmeddarwish_cloudflare.ini  -d bus.esolvelabs.com  --email info@esolvelabs.com --agree-tos --non-interactive --force-renewal --cert-name bus.esolvelabs.com --keep-until-expiring --rsa-key-size 4096



