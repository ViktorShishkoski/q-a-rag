# Widget Framework

The Widget Framework is a lightweight toolkit for building modular user interfaces.
It focuses on composability and predictable state management.

## Installation

Install the framework using your package manager of choice.

### Requirements

The framework requires Python 3.11 or newer and at least 512MB of available memory.
No GPU is required for standard usage.

## Configuration

Configuration is handled through a single `widget.toml` file placed at the
project root. The framework reads this file once at startup and validates it
against a strict schema before continuing.

### Environment Variables

Several settings can be overridden via environment variables, which always
take precedence over values found in `widget.toml`. This is useful for
container deployments where the configuration file is baked into an image.

## Usage

Once configured, widgets are declared using a simple builder API. Each widget
is immutable once constructed, which makes the resulting UI tree easy to
reason about and test.
