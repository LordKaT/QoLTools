Automated tool for updating things without GUI or user prompting.

To use automaticallyin Debian 13:

Copy this script to a local folder:

```
mkdir ~/.local/share/qolupdater
cp qolupdater.sh ~/.local/share/qolupdater
cp discord-updater.sh ~/.local/share/qolupdater
chmod +x ~/.local/share/qolupdater/qolupdater.sh
chmod +x ~/.local/share/qolupdater/discord-updater.sh
```

Add a user specific systemd service:

```
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/qolupdater.service
```

qolupdater.servce:

```
[Unit]
Description=Unattended Updater

[Service]
Type=oneshot
ExecStart=%h/.local/share/qolupdater/qolupdater.sh
```

Add a timer for the service:

```
nano ~/.config/systemd/user/qolupdater.timer
```

qolupdater.timer:

```
[Unit]
Description=Run QoLUpdater every day at 4am

[Timer]
OnCalendar=*-*-* 04:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable the timer:

```
systemctl --user daemon-reload
systemctl --user enable --now qolupdater.timer
systemctl --user list-timers | grep qolupdater
```

Give your script passwordless sudo for apt updated:

```
sudo visudo -f /etc/sudoers.d/qolupdater
```

Inside the qolupdater sudoers.d file:

```
YOUR_USERNAME ALL=(ALL:ALL) NOPASSWD: /usr/bin/apt-get update
YOUR_USERNAME ALL=(ALL:ALL) NOPASSWD: /usr/bin/apt-get upgrade
YOUR_USERNAME ALL=(ALL:ALL) NOPASSWD: /usr/bin/apt-get upgrade *
YOUR_USERNAME ALL=(ALL:ALL) NOPASSWD: /usr/bin/apt-get autoremove
YOUR_USERNAME ALL=(ALL:ALL) NOPASSWD: /usr/bin/apt-get autoremove *
YOUR_USERNAME ALL=(ALL:ALL) NOPASSWD: /usr/bin/apt-get install *
YOUR_USERNAME ALL=(ALL:ALL) NOPASSWD: /usr/bin/apt-get remove *
YOUR_USERNAME ALL=(ALL:ALL) NOPASSWD: /usr/bin/apt update
YOUR_USERNAME ALL=(ALL:ALL) NOPASSWD: /usr/bin/apt upgrade
YOUR_USERNAME ALL=(ALL:ALL) NOPASSWD: /usr/bin/apt upgrade *
YOUR_USERNAME ALL=(ALL:ALL) NOPASSWD: /usr/bin/apt autoremove
YOUR_USERNAME ALL=(ALL:ALL) NOPASSWD: /usr/bin/apt autoremove *
YOUR_USERNAME ALL=(ALL:ALL) NOPASSWD: /usr/bin/apt install *
YOUR_USERNAME ALL=(ALL:ALL) NOPASSWD: /usr/bin/apt remove *
```

Is this dangerous? Yes, probably. Do I care? Not really.

Run the timer and the service:
```
systemctl --user start qolupdater.timer
systemctl --user start qolupdater.service
```

To verify it's working, check the log:

```
journalctl --user -u qolupdater.service -n 30 --no-pager
```

You should see something like this:
```
felicia@bastok:~$ journalctl | grep qolupdater
Nov 20 06:18:24 bastok sudo[3174936]: pam_unix(sudo:session): session closed for user root
Nov 20 06:18:25 bastok qolupdater.sh[3174861]: Repo: /home/felicia/Projects/yt-dlp
Nov 20 06:18:25 bastok qolupdater.sh[3174861]: Current branch: master
Nov 20 06:18:25 bastok qolupdater.sh[3174861]: Default branch: master
Nov 20 06:18:25 bastok qolupdater.sh[3174861]: → Updating current branch: master
Nov 20 06:18:25 bastok qolupdater.sh[3174977]: Already up to date.
Nov 20 06:18:25 bastok qolupdater.sh[3174861]: ✓ Already on default branch; update complete.
Nov 20 06:18:25 bastok qolupdater.sh[3174861]: Repo: /home/felicia/Projects/bandcamp-dl
Nov 20 06:18:25 bastok qolupdater.sh[3174861]: Current branch: master
Nov 20 06:18:25 bastok qolupdater.sh[3174861]: Default branch: master
Nov 20 06:18:25 bastok qolupdater.sh[3174861]: → Updating current branch: master
Nov 20 06:18:25 bastok qolupdater.sh[3174861]: ✓ Already on default branch; update complete.
Nov 20 06:18:25 bastok qolupdater.sh[3174861]: Repo: /home/felicia/Projects/ws4kp
Nov 20 06:18:25 bastok qolupdater.sh[3174861]: Current branch: main
Nov 20 06:18:25 bastok qolupdater.sh[3174861]: Default branch: main
Nov 20 06:18:25 bastok qolupdater.sh[3174861]: → Updating current branch: main
Nov 20 06:18:26 bastok qolupdater.sh[3174861]: ✓ Already on default branch; update complete.
Nov 20 06:18:26 bastok qolupdater.sh[3174861]: Repo: /home/felicia/Projects/ffxi/server
Nov 20 06:18:26 bastok qolupdater.sh[3174861]: Current branch: base
Nov 20 06:18:26 bastok qolupdater.sh[3174861]: Default branch: base
Nov 20 06:18:26 bastok qolupdater.sh[3174861]: → Updating current branch: base
Nov 20 06:18:26 bastok qolupdater.sh[3174861]: ✓ Already on default branch; update complete.
Nov 20 06:18:26 bastok qolupdater.sh[3174861]: Repo: /home/felicia/Projects/ffxi/xiloader
Nov 20 06:18:26 bastok qolupdater.sh[3174861]: Current branch: main
Nov 20 06:18:26 bastok qolupdater.sh[3174861]: Default branch: main
Nov 20 06:18:26 bastok qolupdater.sh[3174861]: → Updating current branch: main
Nov 20 06:18:26 bastok qolupdater.sh[3174861]: ✓ Already on default branch; update complete.
Nov 20 06:18:26 bastok qolupdater.sh[3174861]: Discord updater
Nov 20 06:18:28 bastok systemd[1629]: Finished qolupdater.service - Automatic Updater.
Nov 20 06:18:28 bastok systemd[1629]: qolupdater.service: Consumed 2.276s CPU time, 241.7M memory peak.
```

Yes, I name my machines based off FFXI city names.

Debug as needed.
