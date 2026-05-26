# cmi5 demo example

[![Documentation](https://readthedocs.org/projects/lxpack/badge/?version=latest)](https://lxpack.readthedocs.io/en/latest/?badge=latest)

Security-awareness course configured for cmi5 packaging.

**Docs:** [Export to LMS](https://lxpack.readthedocs.io/en/latest/guides/export-to-lms/) · [Tracking and completion](https://lxpack.readthedocs.io/en/latest/reference/tracking-and-completion/) · [course.yaml — tracking.xapi](https://lxpack.readthedocs.io/en/latest/reference/course-yaml/) · [@lxpack/cmi5](../../packages/cmi5/README.md).

```bash
cd examples/cmi5-demo
lxpack validate
lxpack build
```

`lxpack.config.json` sets `defaultTarget` to `cmi5`, so `validate` and `build` pick up cmi5 rules without `--target`.

Import the package into a cmi5-aware LMS. The LMS supplies LRS credentials via launch URL parameters (not embedded in the ZIP). Authoring overview: [Build courses](https://lxpack.readthedocs.io/en/latest/guides/build-overview/).
