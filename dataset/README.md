# The Goodenough dataset
We set out to create a dataset that better reflects the challenges of an
attacker than the typical datasets used in the evaluation of Website
Fingerprinting attacks. The dataset consists of 10,000 monitored samples and
10,00 unmonitored samples. The monitored samples represent 50 classes of popular
websites taken from the Alexa toplist (all within Alexa top-300 at the time of
collection). For each website/class, we selected 10 webpages to represent that
class, with the intent of evaluating _webpage-to-website_ fingerprinting. For
example, for the website reddit.com, we selected 10 URLs to popular subreddits
such as https://www.reddit.com/r/wholesomememes/. Similarly, for wikipedia.org,
we selected articles such as https://en.wikipedia.org/wiki/Dinosaur, etc. The
full list of websites and webpages are available as part of the dataset. We
collected 20 samples per webpage, resulting in 50x10x20=10,000 monitored
samples.

As a complement, we collected 10,000 unmonitored webpages from reddit.com/r/all
(top last year). We made sure to exclude webpages of monitored websites, which
include self-hosted images at Reddit. We also excluded direct image links, since
they are too distinct to the monitored webpages, and links to YouTube and
Twitter that have a tendency of not treating traffic from Tor nicely (i.e.,
sporadically blocking access).

The dataset consists of:
- lists of visited monitored and unmonitored websites
- logs from Tor Browser
- traces extracted for the circuit padding simulator
- fakerelay traces that are simulated from the client traces

The final traces have all been verified to work fine with the circuit padding
simulator.

We collected the dataset so far in the beginning of January and February to
allow for comparisons over time. We did minimal changes to the webpages visited
due to, .e.g., removed content. See list README for details of our changes.

Download links (may change in the future, please reference this repository):
- https://dart.cse.kau.se/goodenough/goodenough-jan-2020.zip
- https://dart.cse.kau.se/goodenough/goodenough-feb-2020.zip

```
$ sha256sum goodenough-*
37ab85288ebd8c9059b93716e2b21235a06063d252242f01c4274d0605e28131  goodenough-feb-2020.zip
82123a774275b9b6830a9208591f4e9c7bf759d12ed690db8694362fbca9bcac  goodenough-jan-2020.zip
```
