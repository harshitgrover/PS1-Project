# Handling New Constraint Types

This is a structured rule, not Python code:

```json
{
  "type": "daylight_requirement",
  "room": "Bedroom",
  "min_hours": 2,
  "season": "winter"
}
```

It means:

```text
Bedroom must receive at least 2 hours of daylight during winter.
```

Your current engine probably does not support this rule type yet.

To support it as a real product feature, the fixed Python backend would need logic in:

```text
rule_schema.py
-> allow "daylight_requirement"

rule_parser.py
-> convert user text into this JSON rule

rule_compiler.py
-> convert daylight rule into solver constraints or call daylight analysis

rule_verifier.py
-> verify the final layout actually satisfies the daylight requirement
```

Daylight is more complex than simple room placement.

For daylight verification, Python would need extra inputs:

```json
{
  "type": "daylight_requirement",
  "room": "Bedroom",
  "min_hours": 2,
  "season": "winter",
  "location": "Ahmedabad, India",
  "window_orientation": "east",
  "date_range": "winter_solstice"
}
```

Daylight depends on:

```text
site location
sun path
season/date
window position
room orientation
nearby obstructions
building height
wall openings
```

So this rule is a good example of a new product capability, not just a new user constraint.

Once `daylight_requirement` is implemented generically, future users can say:

```text
Bedroom needs 2 hours of winter daylight.
Living Area needs 4 hours of morning sunlight.
Study room should avoid harsh west sunlight.
```

The same deployed code can then handle those requests without per-user code changes.

## LLM as a Rule Form Filler

Think of the LLM as a form-filling system.

The backend already knows the rule format it supports.

Example supported format:

```json
{
  "type": "daylight_requirement",
  "room": "",
  "min_hours": "",
  "season": "",
  "location": ""
}
```

Required fields are:

```text
room
min_hours
season
location
```

Now the user says:

```text
Bedroom needs winter daylight.
```

The LLM converts this sentence into partial JSON:

```json
{
  "type": "daylight_requirement",
  "room": "Bedroom",
  "season": "winter"
}
```

The Python backend checks this JSON against the supported format.

It sees:

```text
room: present
season: present
min_hours: missing
location: missing
```

So the product asks the user:

```text
How many minimum daylight hours are required?
What is the site location?
```

The user replies:

```text
2 hours, Ahmedabad
```

Now the backend completes the rule:

```json
{
  "type": "daylight_requirement",
  "room": "Bedroom",
  "min_hours": 2,
  "season": "winter",
  "location": "Ahmedabad"
}
```

Then this valid rule goes into the solver or verifier.

## Extra Fields

If the user says:

```text
Kitchen should be southeast and blue color.
```

The LLM may return:

```json
{
  "type": "zone",
  "room": "Kitchen",
  "zone": "southeast",
  "color": "blue"
}
```

The backend checks the `zone` rule format:

```json
{
  "type": "zone",
  "room": "",
  "zone": ""
}
```

Required fields are:

```text
room
zone
```

It sees:

```text
room: present
zone: present
color: extra
```

So the backend ignores `color` because the layout solver does not need it:

```json
{
  "type": "zone",
  "room": "Kitchen",
  "zone": "southeast"
}
```

No user follow-up is needed.

Product behavior:

```text
Missing required field = ask user
Extra unsupported field = ignore or save as note
Unsupported rule type = tell user it is not supported yet
```

Important idea:

```text
LLM does not change code.
LLM only fills JSON.
Python backend checks if JSON is complete and valid.
```
