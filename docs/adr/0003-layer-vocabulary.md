# One vocabulary for pipeline layers

Layers are named `landing`, `raw`, `staging`, `intermediate`, `marts`. The
medallion names — bronze, silver, gold — are not used anywhere in the codebase,
documentation or conversation.

## Consequences

The project's first plan carried three overlapping vocabularies at once:
raw/staging, bronze/silver/gold, and dbt's staging/intermediate/marts. The word
"staging" appeared in two of them meaning different layers, and "silver" could
credibly point at either a warehouse schema or a dbt model directory. Nobody can
explain a data flow they cannot name unambiguously.

The mapping to the medallion pattern is documented once, in the README, for
readers who expect that vocabulary. It is not used as working language.
