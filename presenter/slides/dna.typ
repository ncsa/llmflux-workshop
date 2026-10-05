// The DNA strip from the deck's master slide, redrawn as vector shapes.
// Measurements are taken from the original PowerPoint master.
//
// Use it as a page background:
//   #import "dna.typ": dna
//   #set page(background: place(left + top, dx: 1cm, dy: 0.1cm, dna()))

#let rung-color = rgb("#2A6099")
#let blue-outline = rgb("#2A6099")
#let orange-outline = rgb("#FF4000")

// One full turn of the helix is 10 rows. For each row:
//   how far the two circles sit from the center line (cm),
//   whether the blue circle is on the left,
//   blue circle fill and outline width, orange circle fill and outline width.
// The outline widths change through the turn so the near side looks closer.
#let turn = (
  (1.011, true,  "#BCC2C9", 1.28pt, "#F2CDC4", 1.56pt),
  (1.250, true,  "#C7CED6", 1.42pt, "#E6C2B9", 1.42pt),
  (1.011, true,  "#D3DAE3", 1.56pt, "#D9B8AF", 1.28pt),
  (0.386, true,  "#DEE6EF", 1.70pt, "#CCADA5", 1.13pt),
  (0.386, false, "#DEE6EF", 1.70pt, "#CCADA5", 1.13pt),
  (1.011, false, "#D3DAE3", 1.56pt, "#D9B8AF", 1.28pt),
  (1.250, false, "#C7CED6", 1.42pt, "#E6C2B9", 1.42pt),
  (1.011, false, "#BCC2C9", 1.28pt, "#F2CDC4", 1.56pt),
  (0.386, false, "#AFB6BD", 1.13pt, "#FFD8CE", 1.70pt),
  (0.386, true,  "#AFB6BD", 1.13pt, "#FFD8CE", 1.70pt),
)

#let dna(rows: 27, pitch: 0.6cm, size: 0.5cm) = {
  let axis = 1.5cm  // the helix's center line, from the strip's left edge
  box(width: 3cm, height: rows * pitch, {
    for i in range(rows) {
      let (half, blue-left, blue-fill, blue-w, orange-fill, orange-w) = turn.at(calc.rem(i, 10))
      let y = i * pitch + size / 2
      let left-x = axis - half * 1cm
      let right-x = axis + half * 1cm
      let blue = circle(radius: size / 2, fill: rgb(blue-fill), stroke: blue-w + blue-outline)
      let orange = circle(radius: size / 2, fill: rgb(orange-fill), stroke: orange-w + orange-outline)
      let (left, right) = if blue-left { (blue, orange) } else { (orange, blue) }

      // The rung first, so the circles cover its ends.
      place(line(start: (left-x, y), end: (right-x, y), stroke: 1.42pt + rung-color))
      place(dx: left-x - size / 2, dy: y - size / 2, left)
      place(dx: right-x - size / 2, dy: y - size / 2, right)
    }
  })
}
