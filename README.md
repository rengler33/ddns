# ddns (Cloudflare)

Update the content of a Cloudflare DNS record with ip as fetched from ipify.org or httbin.org.

## Setup

Copy `config.toml.example` to `config.toml`. Fill in values.

You will need to know the id of the record you intend to update.
You will need an application token from Cloudflare.


## Behavior

Script will save the last ip fetched to `last_ip.txt` if it succesfully updates Cloudfare.
If the same IP is seen on the next run, it will not attempt to update Cloudflare.
