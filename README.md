# Some DevNet scripts

## mpsg500.py

Interface data from cisco sg500 switches:

|hostname     |type     |duplex|speed|state|int  |vlan|descr|mac              |log1|
|-------------|---------|------|-----|-----|-----|----|-----|-----------------|----|
|ZC01-ACCESW01|1G-Copper|Full  |1000 |Up   |gi1/1|51  |     |00:07:5f:a6:bb:d5|"16-Apr-2019 21:30:45 :%LINK-I-Up:  gi1/1 \n 16-Apr-2019 21:30:42 :%LINK-W-Down:  gi1/1"	|
|             |1G-Copper|Full  |1000 |Up   |gi1/2|51  |     |ac:cc:8e:b3:e9:69|"16-Apr-2019 21:30:46 :%LINK-I-Up:  gi1/2 \n 16-Apr-2019 21:30:42 :%LINK-W-Down:  gi1/2"	|	
|             |1G-Copper|Full  |1000 |Up   |gi1/3|51  |     |00:07:5f:a6:be:24|"16-Apr-2019 21:30:46 :%LINK-I-Up:  gi1/3 \n 16-Apr-2019 21:30:42 :%LINK-W-Down:  gi1/3" |

Data for connection (json file):

```
{
    "CampusName": {
        "login": "login",
        "pass" : "pass",
        "port" : 22,
        "devices": [
            "172.16.0.10",
            "172.16.0.11",
            "172.16.0.12"
        ]
    }
}
```