# xAPI awareness example

[![Documentation](https://readthedocs.org/projects/lxpack/badge/?version=latest)](https://lxpack.readthedocs.io/en/latest/?badge=latest)

Fork of `security-awareness` with `tracking.xapi.activityIri` for Tin Can export.

**Docs:** [Export to LMS](https://lxpack.readthedocs.io/en/latest/guides/export-to-lms/) · [Tracking and completion](https://lxpack.readthedocs.io/en/latest/reference/tracking-and-completion/) · [course.yaml — tracking.xapi](https://lxpack.readthedocs.io/en/latest/reference/course-yaml/) · [@lxpack/xapi](../../packages/xapi/README.md).

```bash
cd examples/xapi-awareness
lxpack validate
lxpack build
```

`lxpack.config.json` sets `defaultTarget` to `xapi`, so `validate` and `build` pick up xAPI rules without `--target`.

Upload the ZIP to an LRS or open `index.html` with launch query params (`endpoint`, `auth`, `actor`, `registration`). See [CLI reference](https://lxpack.readthedocs.io/en/latest/reference/cli/) for build options.
