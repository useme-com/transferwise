#!/bin/sh
PRVKEY=prvkey.pem
PUBKEY=pubkey.pem
openssl genrsa -out $PRVKEY 2048 && \
openssl rsa -pubout -in $PRVKEY -out $PUBKEY && \
echo -e "\n\nPrivate key file: $PRVKEY" && \
echo " Public key file: $PUBKEY" && \
echo -e "\n\nAdd $PUBKEY into Manage your public keys section in TransferWise settings."
