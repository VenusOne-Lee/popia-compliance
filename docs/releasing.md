# Releasing

Pushing a tag like `v1.1.0` runs `.github/workflows/release.yml`. It checks that the tag matches the version in `pyproject.toml`, `package.json` and `scripts/cli.py`, runs the tests, builds the files, then publishes to PyPI and npm and creates a GitHub release.

PyPI and npm use trusted publishing. GitHub proves which workflow is publishing, so there are no long-lived tokens to leak.

## One-time setup

### PyPI

1. Sign in at pypi.org with an account that has two-factor authentication.
2. Go to Your account, Publishing, and add a pending publisher:
   - PyPI project name: `popia-kit`
   - Owner: `VenusOne-Lee`
   - Repository name: `popia-compliance`
   - Workflow name: `release.yml`
   - Environment name: `pypi`

The first release creates the project.

### npm (off by default)

The npm job only runs when the repository variable `PUBLISH_NPM` is `true` (Settings, Secrets and variables, Actions, Variables). Until then, releases go to PyPI and GitHub only.

npm can only add a trusted publisher to a package that already exists. The first release uses a token, then you switch.

1. Sign in at npmjs.com with two-factor authentication on.
2. Create a granular access token: read and write, limited to packages, 7 day expiry.
3. In GitHub, go to Settings, Secrets and variables, Actions, and add it as `NPM_TOKEN`.
4. After the first release, open the `popia-kit` package on npmjs.com, go to Settings, Trusted publishing, and add GitHub Actions with owner `VenusOne-Lee`, repository `popia-compliance`, workflow `release.yml`, environment `npm`.
5. Delete the `NPM_TOKEN` secret in GitHub and revoke the token on npmjs.com.

### GitHub environments

In GitHub, go to Settings, Environments, and create `pypi` and `npm`. Add yourself as a required reviewer on both, so nothing publishes without your click.

## Each release

1. Update the version in `pyproject.toml`, `package.json` and `scripts/cli.py`.
2. Move the `Unreleased` section of `CHANGELOG.md` under the new version and date.
3. Merge to `main`, then tag and push:

   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```

4. Approve the two deployments in the Actions tab.

Engineering guidance, not legal advice.
