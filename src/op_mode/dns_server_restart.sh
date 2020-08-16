#!/bin/sh

if cli-shell-api existsEffective service dns server; then
    echo "Restarting the DNS server service"
    systemctl restart pdns-server
else
    echo "DNS server is not configured"
fi
