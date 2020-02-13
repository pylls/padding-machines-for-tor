# Simple helper script. The two runs used for the goodenough dataset using their
# respective lists (see zips). I manually (un)commented the lines below per
# part, the server won't stop when done.

#python3.6 circpad-server.py -d safer-mon/ -l top-50-selected-multi.list -n 30 -m 100
python3.6 circpad-server.py -d safer-unmon/ -l reddit-front-year.list -n 1 -s 11000 -m 100
