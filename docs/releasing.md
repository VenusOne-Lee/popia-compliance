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

1. Update the version in `pyproject.toml`, `package.json`, `scripts/cli.py` and both `version` fields in `server.json`. A unit test fails if they differ.
2. Move the `Unreleased` section of `CHANGELOG.md` under the new version and date.
3. Merge to `main`. Then either publish a release in GitHub (Releases, Draft a new release, new tag `v1.1.0` on `main`, Publish), or tag and push:

   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```

4. Approve the two deployments in the Actions tab.
5. Update the listing in the MCP Registry once the new version is on PyPI. See below.

## MCP Registry

`server.json` describes the MCP server for the [official MCP Registry](https://registry.modelcontextprotocol.io), which Claude, Cursor, VS Code and other clients use to find servers. The registry checks that the PyPI package is ours by finding the line `mcp-name: io.github.VenusOne-Lee/popia-kit` in the README, which is the PyPI description. That line is a hidden comment near the top of README.md. Keep it there.

The first listing needs a PyPI release that already carries that line. After each release:

1. Install the publisher: download `mcp-publisher` from the registry's GitHub releases, or `brew install mcp-publisher`.
2. From the repository root on `main`: `mcp-publisher login github`. Sign in as VenusOne-Lee in the browser.
3. `mcp-publisher publish`. It reads `server.json`.
4. Check it is listed: `curl "https://registry.modelcontextprotocol.io/v0/servers?search=popia-kit"`.

Engineering guidance, not legal advice.
