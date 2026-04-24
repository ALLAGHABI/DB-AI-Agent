#!/bin/bash
open "http://localhost:8080"
sleep 1
osascript -e 'tell application "Terminal" to close (every window whose name contains "open_browser")' &
exit 0
