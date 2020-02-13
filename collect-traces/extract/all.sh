# we assume that raw contains folders as collected by `circpad-server.py` with the same lists

# extract monitored
./extract.py -i raw/safer-mon/ -o safer/client-logs/monitored/ -t safer/client-traces/monitored/ -l top-50-selected-multi.list --monitored
./extract.py -i raw/safest-mon/ -o safest/client-logs/monitored/ -t safest/client-traces/monitored/ -l top-50-selected-multi.list --monitored
./extract.py -i raw/standard-mon/ -o standard/client-logs/monitored/ -t standard/client-traces/monitored/ -l top-50-selected-multi.list --monitored
# extract unmonitored
./extract.py -i raw/safer4-unmon/ -o safer/client-logs/unmonitored/ -t safer/client-traces/unmonitored/ -l reddit-front-year.list --unmonitored
./extract.py -i raw/safest4-unmon/ -o safest/client-logs/unmonitored/ -t safest/client-traces/unmonitored/ -l reddit-front-year.list --unmonitored
./extract.py -i raw/standard-unmon/ -o standard/client-logs/unmonitored/ -t standard/client-traces/unmonitored/ -l reddit-front-year.list --unmonitored

# simulate fake relay traces
./simrelaytrace.py -i safer/client-traces/monitored/ -o safer/fakerelay-traces/monitored/
./simrelaytrace.py -i safer/client-traces/unmonitored/ -o safer/fakerelay-traces/unmonitored/
./simrelaytrace.py -i safest/client-traces/monitored/ -o safest/fakerelay-traces/monitored/
./simrelaytrace.py -i safest/client-traces/unmonitored/ -o safest/fakerelay-traces/unmonitored/
./simrelaytrace.py -i standard/client-traces/monitored/ -o standard/fakerelay-traces/monitored/
./simrelaytrace.py -i standard/client-traces/unmonitored/ -o standard/fakerelay-traces/unmonitored/
