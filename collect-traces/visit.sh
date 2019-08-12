echo "visiting $1 with TB at $2, timeout $3"
timeout -k 5 $3 $2 --headless $1