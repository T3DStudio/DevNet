random=$(head /dev/urandom | tr -dc 'A-Za-z0-9!@#&' | head -c 8 ; echo '')

ssid="SSIDNAME"
wifi="WIFI:T:WPA;S:"$ssid";P:"$random";;"

WLC_Login=root
WLC_pass=fdgdfg435

qrencode -o psk.png -s 6 $wifi

MAILTO="pi@vlab.free,admin@vlab.free"
FROM="psk@vlab.free"
SUBJECT="GUEST Wi-Fi - New PSK"
BODY="$random"
ATTACH="psk.png"
(
 echo "To: $MAILTO"
 echo "Subject: $SUBJECT"
 echo "Mime-Version: 1.0"
 echo 'Content-Type: multipart/mixed; boundary="19032019ABCDE"'
 echo '--19032019ABCDE'
 echo 'Content-Type: text/plain; charset="UTF-8"'
 echo 'Content-Disposition: inline'
 echo ''
 echo $BODY
 echo '--19032019ABCDE'
 echo 'Content-Type: image/png; name="'$ATTACH'"'
 echo "Content-Transfer-Encoding: base64"
 echo 'Content-Disposition: attachment; filename="'$ATTACH'"'
 uuencode --base64 $ATTACH $ATTACH
 echo '--19032019ABCDE--'
) | /usr/sbin/sendmail -f "${FROM}" -t "${MAILTO}"

curl -H "Content-Type:application/json" \
     -d '{
  "cliTemplateCommand" : {
    "options" : {
      "copyConfigToStartup" : true
    },
    "targetDevices" : {
      "targetDevice" : [ {
        "targetDeviceID" : "2354352",
        "variableValues" : {
          "variableValue" : [ {
            "name" : "PSK",
            "value" : "'"$random"'"
          } ]
        }
      } ]
    },
    "templateName" : "PSK"
  }
}' \
-k -X PUT -u $WLC_Login:$WLC_pass https://localhost/webacs/api/v2/op/cliTemplateConfiguration/deploy.json