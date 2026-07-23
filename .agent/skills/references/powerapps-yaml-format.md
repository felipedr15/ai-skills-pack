---
name: Power Apps YAML Format
id: powerapps-yaml-format
version: 1.0.0
description: Reference for the YAML-based code format Power Apps accepts for screen definitions, control hierarchies, and property expressions.
triggers:
  - powerapps
  - power apps
  - power apps code
  - pa.yaml
  - power apps yaml
inputs:
  - power apps screen or control requirements
outputs:
  - valid power apps yaml code
dependencies: []
status: stable
replaces: null
deprecatedBy: null
---

# Power Apps YAML Code Format Reference

## Purpose

Define the exact YAML-based coding input format that Power Apps accepts. Use this when generating, editing, or reviewing Power Apps source files (`.pa.yaml`).

## File Structure

```yaml
Screens:
  scrScreenName:
    Properties:
      PropertyName: =Expression
    Children:
      - ControlName:
          Control: ControlType@Version
          Variant: VariantName
          Properties:
            PropertyName: =Expression
          Children:
            - NestedControlName:
                ...
```

## Expression Syntax

All property values begin with `=` to denote a Power Fx expression.

### Single-line

```yaml
Fill: =RGBA(56, 96, 178, 1)
Text: ="Hello World"
Visible: =!gblAccessDenied
Width: =Parent.Width
```

### Multi-line (block scalars)

Use `|-` followed by `=` on the first content line:

```yaml
OnSelect: |-
  =Set(gblIsLoading, true);
  Refresh('ScheduleEntries List');
  Set(gblIsLoading, false)
```

Or use `|=` which embeds the `=` in the block indicator:

```yaml
OnSelect: |=
  Set(gblIsLoading, true);
  Refresh('ScheduleEntries List');
  Set(gblIsLoading, false)
```

Combined `|-=` for inline multi-statement:

```yaml
OnChange: |-
  =Set(gblCurrentPage, 1);
  Select(btnRefreshMonth)
```

The `|+=` variant is valid for multi-line property values (observed on Visible):

```yaml
Visible: |+=
  gblIsManagement
```

## Control Types

### Modern Controls (no prefix)

| Control | Example |
|---------|---------|
| `Label@2.5.1` | Text display |
| `Button@0.0.45` | Clickable button |
| `ComboBox@0.0.51` | Dropdown / multi-select |
| `GroupContainer@1.5.0` | Layout container |
| `Gallery@2.15.0` | Repeating data list |
| `Rectangle@2.3.0` | Shape |
| `Image@2.2.3` | Image display |
| `Timer@2.1.0` | Timer control |

### Classic Controls (prefix `Classic/`)

| Control | Example |
|---------|---------|
| `Classic/Button@2.2.0` | Legacy button |
| `Classic/Icon@2.5.0` | Icon display |
| `Classic/TextInput@2.3.2` | Text input field |

## Container Layout System

GroupContainers with `Variant: AutoLayout` use a flexbox-like model:

```yaml
- conExample:
    Control: GroupContainer@1.5.0
    Variant: AutoLayout
    Properties:
      LayoutDirection: =LayoutDirection.Vertical
      LayoutAlignItems: =LayoutAlignItems.Center
      LayoutJustifyContent: =LayoutJustifyContent.SpaceBetween
      LayoutGap: =12
      FillPortions: =1
      AlignInContainer: =AlignInContainer.Center
      PaddingTop: =16
      PaddingBottom: =16
      PaddingLeft: =16
      PaddingRight: =16
      RadiusTopLeft: =8
      RadiusTopRight: =8
      RadiusBottomLeft: =8
      RadiusBottomRight: =8
```

### Layout Properties

| Property | Purpose |
|----------|---------|
| `LayoutDirection` | `.Vertical` or `.Horizontal` |
| `LayoutAlignItems` | Cross-axis: `.Center`, `.Stretch`, `.Start` |
| `LayoutJustifyContent` | Main-axis: `.Center`, `.SpaceBetween`, `.End` |
| `LayoutGap` | Spacing between children |
| `LayoutMinHeight` / `LayoutMaxHeight` | Height constraints |
| `LayoutMinWidth` / `LayoutMaxWidth` | Width constraints |
| `FillPortions` | Flex-grow equivalent (0 = fixed size) |
| `AlignInContainer` | Per-child alignment override |

## Enums Reference

```yaml
# Layout
LayoutDirection.Vertical | LayoutDirection.Horizontal
LayoutAlignItems.Center | LayoutAlignItems.Stretch | LayoutAlignItems.Start
LayoutJustifyContent.Center | LayoutJustifyContent.SpaceBetween | LayoutJustifyContent.End
AlignInContainer.Center | AlignInContainer.SetByContainer | AlignInContainer.Start
DropShadow.None | DropShadow.Semibold

# Display
DisplayMode.Edit | DisplayMode.Disabled | DisplayMode.View
FontWeight.Bold | FontWeight.Semibold | FontWeight.Normal | FontWeight.Lighter
Font.'Open Sans' | Font.Lato
Align.Center | Align.Right | Align.Left
VerticalAlign.Top | VerticalAlign.Middle
BorderStyle.None

# Icons
Icon.ChevronLeft | Icon.ChevronRight

# Data
SortOrder.Ascending | SortOrder.Descending
NotificationType.Error
TimeUnit.Days | TimeUnit.Months
```

## Color Functions

```yaml
Fill: =RGBA(56, 96, 178, 1)
Fill: =ColorValue("#90EE90")
Fill: =Color.White
Fill: =Color.Transparent
HoverFill: =ColorFade(RGBA(56, 96, 178, 1), -20%)
BorderColor: =ColorFade(Self.Fill, -15%)
```

## Gallery Pattern

```yaml
- galItems:
    Control: Gallery@2.15.0
    Variant: Vertical        # or Horizontal
    Properties:
      Items: =colData
      TemplatePadding: =0
      TemplateSize: =55      # Row height (Vertical) or column width (Horizontal)
      ShowScrollbar: =false
      Height: =Parent.Height
      Width: =Parent.Width
    Children:
      - lblName:
          Control: Label@2.5.1
          Properties:
            Text: =ThisItem.Name
            OnSelect: =Select(Parent)
```

- Use `ThisItem.FieldName` inside gallery children.
- Use `Select(Parent)` for child control OnSelect to bubble to gallery.
- `TemplateSize` controls row/column size; can be dynamic: `=Self.Width / gblDaysInMonth`.

## Common Power Fx in Properties

### Conditional
```yaml
Fill: =If(ThisItem.IsToday, RGBA(56, 96, 178, 0.15), RGBA(0, 0, 0, 0))
DisplayMode: =If(gblIsEmployee, DisplayMode.Disabled, DisplayMode.Edit)
```

### Data operations
```yaml
Items: =Filter(colEmployees, Bureau.Value = "IT")
Text: =CountRows(colFilteredEmployees)
Text: =CountIf(colEntries, StatusValue = "Office")
```

### String formatting
```yaml
Text: =Text(Date(gblSelectedYear, gblSelectedMonth, 1), "mmmm yyyy")
Text: ="Page " & gblCurrentPage & " of " & gblTotalPages
```

### Self / Parent references
```yaml
HoverFill: =ColorFade(Self.Fill, -10%)
Width: =Parent.Width - 195
Height: =Parent.TemplateHeight
```

### Error handling
```yaml
OnSelect: |-
  =IfError(
    Set(gblIsLoading, true);
    Refresh('ScheduleEntries List');
    Set(gblIsLoading, false),
    Notify("Error: " & FirstError.Message, NotificationType.Error);
    Set(gblIsLoading, false)
  )
```

### Patching SharePoint
```yaml
OnSelect: |=
  Patch('ScheduleEntries List',
    Defaults('ScheduleEntries List'),
    {
      Title: locEmployeeName & " - " & Text(DateValue(gblEditEntryDate), "[$-en-US]mm/dd/yyyy"),
      EmployeeName: locEmployeeName,
      EmployeeEmail: Lower(Trim(gblEditEmployeeEmail)),
      EntryDate: DateValue(gblEditEntryDate),
      Status: {Value: locSaveStatus},
      Notes: txtEditNotes.Text
    }
  )
```

## Naming Conventions

| Prefix | Control Type |
|--------|-------------|
| `scr` | Screen |
| `con` | Container |
| `lbl` | Label |
| `btn` | Button |
| `gal` | Gallery |
| `drp` | ComboBox / Dropdown |
| `txt` | TextInput |
| `ico` | Icon |
| `img` | Image |
| `rec` | Rectangle |
| `crd` | Card container |
| `tmr` | Timer |

## Variable Conventions

| Prefix | Scope |
|--------|-------|
| `gbl` | Global variable (`Set`) |
| `loc` | Screen-local variable (`Set`) |
| `col` | Collection (`ClearCollect` / `Collect`) |

## Critical Rules

1. Every property expression MUST start with `=`.
2. Semicolons separate statements in behavioral properties (OnSelect, OnChange, OnVisible).
3. `Children:` uses YAML list syntax (`- controlName:`).
4. Indentation must be consistent (2-space recommended).
5. Control version numbers are required (`@X.X.X`).
6. Variant is required for GroupContainer (`AutoLayout`) and Gallery (`Vertical`/`Horizontal`).

## Source

Extracted from MWS Master Work Schedule Power App, July 2026.
