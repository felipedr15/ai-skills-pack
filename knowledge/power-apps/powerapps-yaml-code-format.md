# Power Apps YAML Code Format Reference

## Purpose

Document the exact YAML-based coding input format that Power Apps accepts for screen definitions, control hierarchies, and property expressions. This is the format used in Power Apps source files (`.pa.yaml`) and is the expected format when generating or editing Power Apps code.

## File Structure

Power Apps uses a hierarchical YAML structure with the following top-level keys:

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

## Key Syntax Rules

### 1. Property Expressions

All property values begin with `=` to denote a Power Fx expression:

```yaml
Fill: =RGBA(56, 96, 178, 1)
Text: ="Hello World"
Visible: =!gblAccessDenied
Width: =Parent.Width
Height: =Parent.Height - 60
```

### 2. Multi-line Expressions

Use YAML block scalar `|-` or `|=` for multi-line Power Fx:

```yaml
OnSelect: |-
  =Set(gblIsLoading, true);
  Set(gblLoadingMessage, "Loading...");
  Refresh('ScheduleEntries List');
  Set(gblIsLoading, false)
```

The `|=` variant preserves the leading `=` on the first line:

```yaml
OnSelect: |=
  Set(gblIsLoading, true);
  Refresh('ScheduleEntries List');
  Set(gblIsLoading, false)
```

Single-line multi-statement expressions use `|-=` prefix:

```yaml
OnSelect: |-
  =Set(gblCurrentPage, 1);
  Select(btnRefreshMonth)
```

### 3. Control Declaration

Controls are declared with type and version:

```yaml
- lblTitle:
    Control: Label@2.5.1
    Properties:
      Text: ="My Title"

- btnSave:
    Control: Button@0.0.45
    Properties:
      Text: ="Save"

- galEmployees:
    Control: Gallery@2.15.0
    Variant: Vertical
    Properties:
      Items: =colEmployees
```

### 4. Classic vs Modern Controls

Classic controls include a `Classic/` prefix:

```yaml
- btnToday:
    Control: Classic/Button@2.2.0

- icoChevron:
    Control: Classic/Icon@2.5.0

- txtInput:
    Control: Classic/TextInput@2.3.2
```

Modern controls omit the prefix:

```yaml
- lblName:
    Control: Label@2.5.1

- btnAction:
    Control: Button@0.0.45

- drpFilter:
    Control: ComboBox@0.0.51

- recShape:
    Control: Rectangle@2.3.0

- imgPhoto:
    Control: Image@2.2.3

- tmrRefresh:
    Control: Timer@2.1.0
```

### 5. Container Controls

GroupContainers use variants and layout properties:

```yaml
- conMain:
    Control: GroupContainer@1.5.0
    Variant: AutoLayout
    Properties:
      LayoutDirection: =LayoutDirection.Vertical
      LayoutAlignItems: =LayoutAlignItems.Stretch
      LayoutJustifyContent: =LayoutJustifyContent.Center
      LayoutGap: =12
      PaddingBottom: =16
      PaddingLeft: =16
      PaddingRight: =16
      PaddingTop: =16
      Fill: =RGBA(255, 255, 255, 1)
      Width: =Parent.Width
      Height: =Parent.Height
```

### 6. Gallery Template Children

Gallery children represent template controls:

```yaml
- galItems:
    Control: Gallery@2.15.0
    Variant: Vertical
    Properties:
      Items: =colData
      TemplatePadding: =0
      TemplateSize: =55
    Children:
      - lblName:
          Control: Label@2.5.1
          Properties:
            Text: =ThisItem.Name
            OnSelect: =Select(Parent)
```

### 7. Enums and Constants

Power Apps enums are referenced as `EnumName.Value`:

```yaml
LayoutDirection: =LayoutDirection.Vertical
LayoutDirection: =LayoutDirection.Horizontal
LayoutAlignItems: =LayoutAlignItems.Center
LayoutAlignItems: =LayoutAlignItems.Stretch
LayoutJustifyContent: =LayoutJustifyContent.SpaceBetween
LayoutJustifyContent: =LayoutJustifyContent.Center
AlignInContainer: =AlignInContainer.Center
AlignInContainer: =AlignInContainer.SetByContainer
DropShadow: =DropShadow.None
DropShadow: =DropShadow.Semibold
DisplayMode: =DisplayMode.Edit
DisplayMode: =DisplayMode.Disabled
DisplayMode: =DisplayMode.View
FontWeight: =FontWeight.Bold
FontWeight: =FontWeight.Semibold
FontWeight: =FontWeight.Normal
FontWeight: =FontWeight.Lighter
Font: =Font.'Open Sans'
Font: =Font.Lato
Align: =Align.Center
Align: =Align.Right
VerticalAlign: =VerticalAlign.Top
Icon: =Icon.ChevronLeft
Icon: =Icon.ChevronRight
BorderStyle: =BorderStyle.None
SortOrder: =SortOrder.Ascending
SortOrder: =SortOrder.Descending
NotificationType: =NotificationType.Error
TimeUnit: =TimeUnit.Days
TimeUnit: =TimeUnit.Months
```

### 8. Color Functions

```yaml
Fill: =RGBA(56, 96, 178, 1)
Fill: =ColorValue("#90EE90")
Fill: =Color.White
Fill: =Color.Transparent
HoverFill: =ColorFade(RGBA(56, 96, 178, 1), -20%)
BorderColor: =ColorFade(Self.Fill, -15%)
```

### 9. Screen-Level Properties

```yaml
Screens:
  scrHome:
    Properties:
      LoadingSpinnerColor: =RGBA(56, 96, 178, 1)
      OnVisible: |-
        =Set(gblCurrentPage, 1);
        Select(btnRefreshMonth)
```

## Common Layout Properties

| Property | Purpose |
|----------|---------|
| `LayoutDirection` | Vertical or Horizontal flow |
| `LayoutAlignItems` | Cross-axis alignment (Center, Stretch, Start) |
| `LayoutJustifyContent` | Main-axis distribution (Center, SpaceBetween, End) |
| `LayoutGap` | Spacing between children |
| `LayoutMinHeight` | Minimum height constraint |
| `LayoutMinWidth` | Minimum width constraint |
| `LayoutMaxHeight` | Maximum height constraint |
| `LayoutMaxWidth` | Maximum width constraint |
| `FillPortions` | Flex-grow equivalent |
| `AlignInContainer` | Per-child override of parent alignment |
| `PaddingTop/Bottom/Left/Right` | Internal padding |
| `RadiusTopLeft/TopRight/BottomLeft/BottomRight` | Border radius corners |

## Common Power Fx Patterns in Properties

### Conditional logic
```yaml
Fill: =If(ThisItem.IsToday, RGBA(56, 96, 178, 0.15), RGBA(0, 0, 0, 0))
DisplayMode: =If(gblIsEmployee, DisplayMode.Disabled, DisplayMode.Edit)
Visible: =!gblAccessDenied
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

### Self-references
```yaml
HoverFill: =ColorFade(Self.Fill, -10%)
PressedFill: =Self.Color
PressedColor: =Self.Fill
```

### Parent references
```yaml
Width: =Parent.Width
Height: =Parent.Height - 60
Width: =Parent.TemplateWidth
```

## Naming Conventions (observed)

| Prefix | Control Type |
|--------|-------------|
| `scr` | Screen |
| `con` | Container (GroupContainer) |
| `lbl` | Label |
| `btn` | Button |
| `gal` | Gallery |
| `drp` | ComboBox / Dropdown |
| `txt` | TextInput |
| `ico` | Icon |
| `img` | Image |
| `rec` | Rectangle |
| `crd` | Card-style container |
| `tmr` | Timer |

## Variable Naming Conventions (observed)

| Prefix | Scope |
|--------|-------|
| `gbl` | Global variable (Set) |
| `loc` | Local/screen variable (Set, used per-screen) |
| `col` | Collection (ClearCollect/Collect) |

## Notes

- The `=` prefix before every expression is mandatory — it tells Power Apps the value is a formula, not literal text.
- Semicolons (`;`) separate statements in behavioral properties (OnSelect, OnChange, OnVisible).
- `Children:` array uses YAML list syntax (`- controlName:`) to define nested controls.
- Indentation is significant — standard 2-space or consistent indentation is required.
- Properties with `|+=` block scalar are also valid (observed for multi-line Visible expressions).
- `Quoted strings` in OnSelect use escaped quotes: `"=Reset(drpBureau);\r\nReset(drpDiv);..."` is also valid.

## Source

Extracted from MWS Master Work Schedule app `scrHome` screen YAML source code, July 2026.
