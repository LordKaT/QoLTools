# QoLTools
Quality of Life tools for life on linux as a daily driver.


### convert_all.py
Converts all media, recursively, in a folder using ffmpeg.

### discorer-updater.sh
Automatic tool for updating Discord, because they treat their debian package like it's still 2002.

To use automatically in Discord 13:

```
mkdir -p ~/.config/systemd/user
nano ~./config/systemd/user/discord-updater.service

[Unit]
Description=Automatic Discord Updater

[Service]
Type=oneshot
ExecStart=%h/.local/share/discord-updater/discord-updater.sh
```

Change %h/.local/share/discord-updater/discord-updater.sh to point to where you'll keep the discord-updater.sh script.

```
nano ~/.config/systemd/user/discord-updater.timer

[Unit]
Description=Run Discord updater every day at 4am

[Timer]
OnCalendar=*-*-* 04:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Now run a bunch of shell commands to enable the timer:

```
systemctl --user daemon-reload
systemctl --user enable --now discord-updater.timer
systemctl --user list-timers | grep discord
```

You should see something like:

```
Sun 20205-10-20 04:00:00 EDT ... discord-updater.timer
```

If you don't, run this:

```
systemctl --user daemon-reload
systemctl --user start discord-updater.timer
systemctl --user list-timers | grep discord
```

You should see the above line. To verify after the first run:

```
journalctl --user -u discord-updater.service -n 30 --no-pager
```
