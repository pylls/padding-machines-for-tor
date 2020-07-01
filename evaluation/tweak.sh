# example of how to tweak machines stored in tmp-mc and tmp-mr, standard february dataset
./tweak.py --client dataset-feb/standard/client-traces/ --relay dataset-feb/standard/fakerelay-traces/ -t ../tor --mc phase2/strawman-mc --mr phase2/strawman-mr --save tmp.pkl -s $1 -w 8
./once.py --ld tmp.pkl --train -s $1
./overhead.py --ld tmp.pkl
./visualize.py --ld tmp.pkl -s tmp
./visualize.py --ld tmp.pkl -s tmp-nopadding --hide
