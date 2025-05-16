default:
    just help

up:
    just --justfile backend/Justfile --working-directory backend up
    just --justfile frontend/Justfile --working-directory frontend up

down:
    just --justfile frontend/Justfile --working-directory frontend down
    just --justfile backend/Justfile --working-directory backend down

bounce:
    just down
    just up

restart:
    just --justfile backend/Justfile --working-directory backend restart 
    just --justfile frontend/Justfile --working-directory frontend restart
