# Auto-accept invites

Synapse module to automatically accept invites.

Compatible with Synapse v1.84.0 and later.

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
      # will be auto accepted.
      # Defaults to false.
      accept_invites_only_for_direct_messages: false

      # Optional: if set to true, then only invites from local users will be auto 
      # accepted.
      # Defaults to false.
      accept_invites_only_from_local_users: false

      # (For workerised Synapse deployments)
      #
      # This module should only be active on a single worker process at once,
      # otherwise invites may be accepted by multiple workers simultaneously.
      #
      # By default, this module is only enabled on the main process, and is disabled
      # on workers. To choose a worker to run this module on (to reduce load on the
      # main process), specify that worker's configured 'worker_name' below.
      #
      # Any worker may be specified. If this worker does not have the ability to
      # write to Synapse's events stream, it will end up calling out to one that
      # does.
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
