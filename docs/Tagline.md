---
tags:
  - tagline
---


Tagline is basically [[StudioCentral]] vibe coded in two weeks most of it over the last like four days. Anyway, what it amounts to is that the Junior League of Los Angeles has six or seven billion photos on Dropbox and they can't find anything, and it goes the other way too, meaning if they have a photo they've got no idea who's in it or when, where or indeed why it was taken. So I got this dumbass idea in my head to try to make the thing I've tried to make like three times before only this time I'll have the computer do it.

I'm being self-deprecating. The foundational technologies have come so far over the years that it's become practical. The big pain in the neck with [[StudioCentral]] was always the database. You needed one, and it was *really important* and that meant high availability and replication and backups and all this for some photos of women in red skirts? Well nope, these days if you need a database you can sign up in minutes for a managed [[Postgres]] service that'll hook you up with the connection string you need for a safe, encrypted connection to a highly available database for so little money that I swear to god they round small monthly bills down to zero. I'm thinking right now of a service called [Neon](https://neon.tech) which I'm thinking of using for oh shit that brings us back to #tagline!