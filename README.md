# RMon: A (R)esource (Mon)itoring tool
RMon is a high-level metric collection tool for Linux machines written in Python. It collects and logs resource statistics at a configurable regular interval and exports logs for a given run as a CSV log file. It collects basic metrics about Linux subsystems as indicated in the configuration file.

## Dependencies
- Python 2
- The `psutil` library
- Linux's `mpack` and `sendmail` tools


## Install
~~~~
sudo apt-get install python-pip  
sudo pip install setuptools
sudo pip install psutil
sudo apt-get install mpack sendmail
git clone  https://git.cs.umu.se/muyi/rmon.git
~~~~

## Usage
~~~~
username@hostname:~/rmon$ python rmon.py -h
Usage: rmon.py [options]

Options:
  -h, --help            show this help message and exit
  -c CONFIGFILE, --config=CONFIGFILE
                        Path to CONFIGFILE
  -i INTERVAL, --interval=INTERVAL
                        Sampling INTERVAL in secs. Default=20
  -d DURATION, --duration=DURATION
                        Estimated DURATION of run in secs. Default=300
  -l LOGMODE, --logmode=LOGMODE
                        Select (1): STDOUT, (2): File, or (3): DB LOGMODE
                        Default=1
  -s SENDMAIL, --sendmail=SENDMAIL
                        Sends compressed log to provided EMAIL
                        Default=NONE
~~~~

## Configuration file
Here is a snapshot of the config file
```
[general]
subsystems=cpu,mem,disk,net
disks=xvda:/dev/xvda
db=localhost/db_name
log_destination=logs
```
Specify resource to monitor using `subsystems` field, particular disk devices with `disks`, remote/local TSDB with `db` and the destination director of generated log with `log_destination`.

## Misc
Sometimes `sendmail` tends to be slow. Check `/var/log/mail.log` for a message like *"My unqualified host name (hostname) unknown; sleeping for retry"*. This message implies `sendmail` needs a fully-qualified hostname. Edit `/etc/hosts` with `127.0.0.1 localhost.localdomain localhost hostname` and that should fix it.

## To do
- Integrate with a time series database (TSDB) such as [InfluxDB](https://www.influxdata.com/time-series-platform/influxdb/) so that measurements are continuously exported to db.
