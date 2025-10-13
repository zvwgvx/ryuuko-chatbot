# /packages/ryuuko-api/src/__main__.py

# This file is the entry point when you run `python -m ryuuko_api` or `ryuuko-api`.
# Its only job is to call the main function from the runner.

from .runner import main

if __name__ == "__main__":
    main()
