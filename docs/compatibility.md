# Compatibility: which geometry an object answers to

A red row in the project tree means an object measures DOFs that the
geometry it answers to does not have. Nothing is blocked by it — the
object plots, exports and computes as before — but a shape cannot be
drawn on a node that is not there, and a report figure that needs the
geometry will say so. This page is the rule, the marks, and the one
act the rule refuses.

## The rule

An object **linked into a group that holds a geometry** is judged
against that geometry — a link is a declaration that these things
belong together, and the group's geometry is the one its shapes and
channels are meant for. Everything else is judged against the
**active geometry**: the one marked in the tree, or the first one in
the project until one is chosen. Right-click a geometry and choose
**Set as Active Geometry** to change it; the active one is drawn bold
with a bullet beside its icon, because bold alone did not stand out
among the darker real objects.

Every DOF of a data object, shape set or channel table has to be a
node in that geometry, in a direction the node can carry. A geometry
that has the nodes is compatible whatever its units, and a project
with no geometry at all has nothing to judge against and marks
nothing.

## The marks

- **A red row** in the tree, with the reason on hover: how many DOFs
  are missing out of how many, which ones (the first six, then *and N
  more*), and which geometry was asked — for example *3 of 678 shape
  DOFs are not in geometry 'plate': 501X+, 501Y+, 501Z+*.
- **A red sub-row** where the object expands: the record, mode or
  channel that carries the missing DOF is marked, not only its
  parent.
- **The same reason in a script**: `project.compatibility()` returns a
  report whose `issue_for(name)` gives the issue for one object, with
  its `missing_dofs`, and `incompatible_names` lists every marked
  object.

## What is refused

Linking. `project.link` — and the link bar in the window — refuses to
put an object into a group whose geometry lacks its DOFs, and says
which DOFs. A group is a promise that its members fit together, and a
link that broke the promise on the way in would have to be marked red
the moment it was made.

## Why a rule rather than a search

The obvious alternative — an object is compatible if *any* geometry in
the project can display it — was considered and rejected. It reads
naturally with two demonstration models loaded side by side, and it is
wrong the moment a project holds a test geometry and a model geometry
that share node numbers: a shape set would be judged against
whichever happened to fit, and the answer would change when a
geometry was added or removed. The group's geometry, and otherwise the
active one, is an answer the user chose.
