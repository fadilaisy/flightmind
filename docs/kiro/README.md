# Recording our Kiro work

Four layers, from automatic to manual:

1. **The repo.** `.kiro/` is committed from day one. Specs keep their ticked `tasks.md`.
   Every commit ends with a `Kiro:` trailer (`git config commit.template .gitmessage`).
2. **`KIRO.md`.** The "log ticked task" hook adds one line per finished spec task.
   Add the "fixed by hand" part yourself if the hook left it out.
3. **Session notes.** When a chat or spec run is worth telling, save the prompt, the result
   and a screenshot as `sessions/YYYY-MM-DD-topic.md` (template in `sessions/TEMPLATE.md`).
4. **Clips.** 30 to 120 seconds, 1080p, Kiro full screen, no music. Name
   `YYYY-MM-DD_role_feature.mp4`, upload to the shared Drive folder, add a row to `clips.md`.

Every Sunday, Role 1 runs `scripts/kiro-stats`, pastes the output into `KIRO.md` and marks
the two best clips of the week as video candidates.

`setup-prompts.md` holds the prompts for creating our hooks, the reviewer agent and the
specs inside Kiro. Create them in Kiro rather than by hand, and record the first one: the
creation itself is evidence for the write-up.
