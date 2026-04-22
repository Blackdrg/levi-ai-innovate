# HAL-0 Bare-Metal OS Makefile

.PHONY: build run test clean iso

# Requires: rustup component add rust-src, cargo install bootimage
build:
	cargo bootimage

run:
	cargo bootimage run

test:
	cargo test

iso:
	cargo bootimage --target x86_64-hal0.json

clean:
	cargo clean

# Helper for local dev
check:
	cargo check --target x86_64-hal0.json
