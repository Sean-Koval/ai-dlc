## ADDED Requirements

### Requirement: NH-06 Capability-scoped shared project guidance

Generated shared project guidance SHALL derive workflow instructions from the
project's existing selected roles and runtime provider kinds. It SHALL retain
configuration/documentation guidance and every configured required check in
declared order with its command, existing missing-command reporting and the
required project-check command. Generic specification, tracker and knowledge
instructions SHALL apply only to their selected roles. Concrete OpenSpec archive
instructions SHALL apply only to the OpenSpec runtime provider. Built-in merge
instructions SHALL apply only to supported selected GitHub SCM. Built-in finish
instructions SHALL apply only with both supported selected GitHub SCM and a
selected built-in Linear, GitHub Issues, Jira Cloud or Plane tracker; OpenSpec
merged-checkout recovery SHALL additionally require OpenSpec. Required
documentation-gate follow-up instructions SHALL apply only when that gate is
configured as required and merge guidance applies.

Provider-kind aliases and existing `kind`/`type` resolution precedence SHALL match
runtime resolution. Component metadata alone SHALL NOT establish executable
provider capabilities. Rendering SHALL remain offline and SHALL NOT execute
provider adapters or weaken required checks, finish gates or ownership rules.
Provider/bundle/team guidance and authored material SHALL retain their existing
delivery and preservation contracts; selected native clients SHALL receive
equivalent conditional shared guidance.

#### Scenario: Local-only adoption
- **WHEN** a project selects no specification, tracker or SCM role and configures a required check
- **THEN** generated guidance retains configuration, durable documentation and verification instructions, reads an active work record only if present, and omits specification/tracker authority, archive, merge and finish directives
- **AND** it does not claim that local validation completes a tracker lifecycle

#### Scenario: Partial adoption retains only applicable instructions
- **WHEN** OpenSpec is selected without tracker or SCM
- **THEN** specification and archive guidance is present without a merge premise, finish command or merged-checkout recovery
- **WHEN** a built-in tracker and GitHub SCM are selected without a specification role
- **THEN** tracker, merge and finish guidance is present without OpenSpec archive or checkout instructions
- **WHEN** OpenSpec and GitHub SCM are selected without a tracker
- **THEN** specification, archive and merge guidance is present without a finish command or finish checkout instruction

#### Scenario: Full supported delivery retains its safeguards
- **WHEN** OpenSpec, GitHub SCM and any of Linear, GitHub Issues, Jira Cloud or Plane are selected
- **THEN** generated guidance includes specification finalization, tracker authority, archive before merge, pre-merge required checks, work finish and the merge-checkout recovery instruction
- **AND** an empty configured finish-gate list does not suppress the existing mandatory runtime gates or advertise weaker completion

#### Scenario: Custom specification provider is not OpenSpec
- **WHEN** a selected custom specification provider supplies component guidance, including a custom runtime provider that reuses the OpenSpec component
- **THEN** generated shared prose retains generic specification/provider instructions but contains no OpenSpec archive command or OpenSpec checkout recovery directive
- **AND** custom linked guidance is not rewritten

#### Scenario: Runtime aliases determine applicable built-in behavior
- **WHEN** providers select supported built-in runtime kinds through aliases with `kind` or legacy `type`
- **THEN** their shared instructions match the corresponding built-in selections, with `kind` taking precedence over `type`, and component IDs do not override runtime identity

#### Scenario: An extension owns its lifecycle instructions
- **WHEN** a tracker or SCM selection resolves to a custom component without the corresponding built-in runtime kind
- **THEN** its generic role guidance and component links remain available but shared prose does not invent built-in finish support or GitHub merge support for that custom SCM
- **AND** rendering does not execute that extension to discover support

#### Scenario: Documentation gate is optional but declared checks are not
- **WHEN** an applicable merge configuration changes between having and not having a required documentation gate
- **THEN** stale-document-disposition advice appears only with the required gate while every declared required check and its command remains present in both configurations

#### Scenario: Re-rendering narrows only owned instructions
- **WHEN** an intact generated full-delivery section is re-rendered after the project removes provider selections
- **THEN** only inapplicable owned instructions are removed, authored prefix/suffix and required checks are preserved, selected clients receive equivalent updated guidance, and a second render is unchanged
- **AND** an authored edit inside the managed section continues to refuse before writes
