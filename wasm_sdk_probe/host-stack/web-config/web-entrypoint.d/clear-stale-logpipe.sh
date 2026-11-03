# start.sh starts the reader of /var/tmp/logpipe only when it creates the FIFO.  ddev recreates its containers, so it never meets one left behind;
# this stack reuses them, so after a stop or a reboot the FIFO is there, nobody reads it, and supervisord blocks opening it for php-fpm's log
# (PID 1 in wait_for_partner, no apache, no php-fpm, 502 at the router).  Removing it here lets start.sh create the FIFO and its reader again.
rm -f /var/tmp/logpipe
