# Auto-accept invites

Synapse module to automatically accept invites.

Compatible with Synapse v1.57.0 and later.

## Installation

From the virtual environment that you use for Synapse, install this module with:
```shell
pip install synapse-auto-accept-invite
```
(If you run into issues, you may need to upgrade `pip` first, e.g. by running
`pip install --upgrade pip`)

Then alter your homeserver configuration, adding to your `modules` configuration:
```yaml
modules:
  - module: synapse_auto_accept_invite.InviteAutoAccepter
    config:
      # Optional: if set to true, then only invites for direct messages (1:1 rooms)
      # will be auto accepted. Otherwise, all room invites are accepted.
      # Defaults to false.
      accept_invites_only_for_direct_messages: false

      # (For workerised Synapse deployments)
      # If you want to accept invites on a specific worker, specify its instance
      # name here. Otherwise, invites will be processed on the main process.
      #
      # Any worker can be used.
      #
      #worker_to_run_on: workername1
```


### A note about logging

Your Synapse logging configuration should have the following option set in it:

```yaml
disable_existing_loggers: False
```

Without it, logging from this module (and potentially others) may not appear in your logs.


## Development

In a virtual environment with pip ≥ 21.1, run
```shell
pip install -e .[dev]
```

To run the unit tests, you can either use:
```shell
tox -e py
```
or
```shell
trial tests
```

To run the linters and `mypy` type checker, use `./scripts-dev/lint.sh`.


## Releasing

 1. Set a shell variable to the version you are releasing (this just makes
    subsequent steps easier):
    ```shell
    version=X.Y.Z
    ```

 2. Update `setup.cfg` so that the `version` is correct.

 3. Stage the changed files and commit.
    ```shell
    git add -u
    git commit -m v$version -n
    ```

 4. Push your changes.
    ```shell
    git push
    ```

 5. When ready, create a signed tag for the release:
    ```shell
    git tag -s v$version
    ```
    Base the tag message on the changelog.

 6. Push the tag.
    ```shell
    git push origin tag v$version
    ```

 7. Create a source distribution and upload it to PyPI:
    ```shell
    python -m build
    twine upload dist/synapse_auto_accept_invite-$version*
    ```
