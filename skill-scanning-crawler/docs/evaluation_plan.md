# Evaluation Plan

## Discovery effectiveness

Report:

- number of candidate repositories,
- number of confirmed repositories,
- number of valid skills,
- number of rejected candidates,
- curated-list rediscovery rate,
- new repositories discovered outside seeds.

## Validation precision proxy

Manually inspect a sample of accepted and rejected candidates.

Report:

- accepted sample correctness,
- rejected sample correctness,
- common rejection causes.

## Efficiency

Report:

- API calls per valid repository,
- API calls per valid skill,
- cache hit rate,
- retries,
- rate-limit events,
- runtime.

## Dataset quality

Report:

- selected repository count,
- exported skill count,
- file-type distribution,
- owner distribution,
- star distribution,
- duplicate content-hash count,
- archived/fork filtering counts.

## Reproducibility

Verify:

- every selected repo has commit SHA,
- every skill has content hash,
- manifests validate against schema,
- snapshot paths exist.
