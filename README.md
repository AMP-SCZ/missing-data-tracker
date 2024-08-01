# missing-data-tracker

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.13151571.svg)](https://doi.org/10.5281/zenodo.13151571) [![Python](https://img.shields.io/badge/Python-3.9-green.svg)]() [![Platform](https://img.shields.io/badge/Platform-linux--64-orange.svg)]()

Web app that tracks missing data

Tashrif Billah and Sylvain Bouix


### Nginx config

To access the web app at https://NAME.harvard.edu/missing , add this snippet to `/etc/nginx/nginx.conf`:

```
    location /missing/ {
        proxy_pass http://127.0.0.1:8052;
    }
```

