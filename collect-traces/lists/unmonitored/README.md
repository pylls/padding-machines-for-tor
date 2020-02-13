# Unmonitored lists from reddit
Using the praw library to access the reddit API, on the 4th of December 2019:

- `reddit-front-year.list` consists of 11716 URLs filtered from 51070
  submissions to r/frontpage limited to submissions this year
- `reddit-front-all.list` consists of 14167 URLs filtered from 54512 submissions
  to r/frontpage wit no time filter (all)

The filtering was done with `reddit.py`, using its built-in blacklist, as well
as the monitored file `top-50-selected-multi.list`.
