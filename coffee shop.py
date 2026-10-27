import math
import turtle
import tkinter as tk

# Beige color palette
BG = '#f5ecd9'
CARD = '#fffaf0'
BORDER = '#d9c7a3'
SHADOW = '#e3d5b8'
ACCENT = '#a67c52'
ACCENT_LIGHT = '#c9a27a'
SOFT = '#e8d9bd'
TEXT = '#4a3728'
MUTED = '#8c7a60'
DISABLED_FILL = '#efe6d2'
DISABLED_LINE = '#e0d5bc'
DISABLED_TEXT = '#b3a58a'
WHITE = '#ffffff'

WIDTH, HEIGHT = 600, 640
DEFAULT_MESSAGE = 'Tap a coffee to add it to your order'


class Coffee:
    # Initialize coffee with name and price
    def __init__(self, name, price):
        self.name = name
        self.price = price


class Order:
    # Initialize order with empty list
    def __init__(self):
        self.items = []

    # Add coffee to order
    def add_item(self, coffee):
        self.items.append(coffee)

    # Remove one coffee with this name from the order
    def remove_one(self, name):
        for i in range(len(self.items) - 1, -1, -1):
            if self.items[i].name == name:
                del self.items[i]
                return

    # Calculate total price
    def total(self):
        return sum(item.price for item in self.items)

    # Group identical items: {name: [count, unit_price]}
    def grouped(self):
        groups = {}
        for item in self.items:
            if item.name not in groups:
                groups[item.name] = [0, item.price]
            groups[item.name][0] += 1
        return groups

    # Remove everything from the order
    def clear(self):
        self.items.clear()


class CoffeeApp:
    # Build the window and draw everything
    def __init__(self, menu):
        self.menu = menu
        self.order = Order()
        self.state = 'menu'  # 'menu', 'confirm' or 'done'
        self.message = DEFAULT_MESSAGE
        self.buttons = []  # (x, y, w, h, callback)
        self.last_total = 0.0
        self.last_count = 0

        self.screen = turtle.Screen()
        self.screen.setup(WIDTH, HEIGHT)
        self.screen.title('Brew Cafe')
        self.screen.bgcolor(BG)
        self.screen.tracer(0)

        static_pen = self._new_pen()
        self.dynamic_pen = self._new_pen()

        # Draw the parts that never change
        self.pen = static_pen
        self.draw_title()
        self.draw_cup()

        # Draw the parts that change with every click
        self.pen = self.dynamic_pen
        self.render()

        self.screen.onclick(self.on_click)

    # Create a hidden, fast turtle
    def _new_pen(self):
        pen = turtle.Turtle()
        pen.hideturtle()
        pen.penup()
        pen.speed(0)
        return pen

    # ---------- Drawing helpers ----------

    # Draw a filled polygon from a list of points
    def polygon(self, points, fill, outline=None, width=2):
        pen = self.pen
        pen.penup()
        pen.goto(points[0])
        pen.color(outline or fill, fill)
        pen.pensize(width if outline else 1)
        pen.pendown()
        pen.begin_fill()
        for point in points[1:]:
            pen.goto(point)
        pen.goto(points[0])
        pen.end_fill()
        pen.penup()
        pen.pensize(1)

    # Draw a rounded rectangle (optionally with a soft shadow)
    def round_rect(self, x, y, w, h, r, fill, outline=None, shadow=False):
        def points(px, py):
            pts = []
            corners = [
                (px + w - r, py + r, -90),
                (px + w - r, py + h - r, 0),
                (px + r, py + h - r, 90),
                (px + r, py + r, 180),
            ]
            for cx, cy, start in corners:
                for step in range(0, 91, 15):
                    angle = math.radians(start + step)
                    pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            return pts

        if shadow:
            self.polygon(points(x + 2, y - 3), SHADOW)
        self.polygon(points(x, y), fill, outline)

    # Draw a filled circle
    def disc(self, cx, cy, r, fill, outline=None):
        pen = self.pen
        pen.penup()
        pen.goto(cx, cy - r)
        pen.setheading(0)
        pen.color(outline or fill, fill)
        pen.pendown()
        pen.begin_fill()
        pen.circle(r)
        pen.end_fill()
        pen.penup()

    # Draw a line through one or more points
    def line(self, points, color, width=2):
        pen = self.pen
        pen.penup()
        pen.goto(points[0])
        pen.color(color)
        pen.pensize(width)
        pen.pendown()
        for point in points[1:]:
            pen.goto(point)
        pen.penup()
        pen.pensize(1)

    # Write text at a position
    def text(self, x, y, content, size=14, color=TEXT,
             align='left', style='normal'):
        self.pen.penup()
        self.pen.goto(x, y)
        self.pen.color(color)
        self.pen.write(content, align=align, font=('Georgia', size, style))

    # ---------- Static design ----------

    # Draw shop name and tagline
    def draw_title(self):
        self.text(0, 262, 'BREW CAFE', 28, TEXT, 'center', 'bold')
        self.text(0, 236, 'Freshly brewed, always', 12, MUTED, 'center', 'italic')
        for side in (-1, 1):
            self.line([(side * 100, 242), (side * 165, 242)], BORDER, 2)

    # Draw a simple coffee cup with saucer, handle and steam
    def draw_cup(self):
        s = 0.46         # Scale
        ox, oy = 0, 135  # Position

        def p(x, y):
            return (ox + s * x, oy + s * y)

        def ellipse(cx, cy, rx, ry):
            return [p(cx + rx * math.cos(math.radians(a)),
                      cy + ry * math.sin(math.radians(a)))
                    for a in range(0, 360, 10)]

        pen = self.pen

        # Saucer
        self.polygon(ellipse(0, 36, 134, 10), SHADOW)
        self.polygon(ellipse(0, 42, 130, 12), BORDER)
        self.polygon(ellipse(0, 45, 92, 7), SOFT)

        # Handle
        pen.penup()
        pen.goto(p(92, 72))
        pen.setheading(0)
        pen.color(ACCENT_LIGHT)
        pen.pensize(6)
        pen.pendown()
        pen.circle(26 * s)
        pen.penup()
        pen.pensize(1)

        # Cup body, rim and coffee
        self.polygon([p(-90, 150), p(90, 150), p(65, 50), p(-65, 50)], ACCENT)
        self.polygon(ellipse(0, 50, 65, 9), ACCENT)
        self.polygon(ellipse(0, 150, 90, 15), ACCENT_LIGHT)
        self.polygon(ellipse(0, 150, 80, 11), TEXT)

        # Steam
        for x in (-35, 0, 35):
            pen.penup()
            pen.color(BORDER)
            pen.pensize(3)
            pen.goto(p(x, 168))
            pen.pendown()
            for step in range(1, 27):
                pen.goto(p(x + 6 * math.sin(step / 3.5), 168 + step))
            pen.penup()
        pen.pensize(1)

    # ---------- Dynamic design (redrawn after every click) ----------

    # Draw a clickable action button
    def action_button(self, x, y, w, h, label, callback,
                      enabled=True, primary=False):
        if not enabled:
            fill, outline, color = DISABLED_FILL, DISABLED_LINE, DISABLED_TEXT
        elif primary:
            fill, outline, color = ACCENT, ACCENT, WHITE
        else:
            fill, outline, color = SOFT, BORDER, TEXT

        self.round_rect(x, y, w, h, 12, fill, outline, shadow=enabled)
        self.text(x + w / 2, y + h / 2 - 8, label, 14, color, 'center', 'bold')
        if enabled:
            self.buttons.append((x, y, w, h, callback))

    # Draw a clickable menu item
    def menu_button(self, index, coffee):
        w, h = 480, 42
        x = -240
        y = 90 - index * 50
        cy = y + h / 2
        enabled = self.state == 'menu'

        if enabled:
            fill, outline = CARD, BORDER
            name_color, price_color, plus_color = TEXT, ACCENT, ACCENT
        else:
            fill, outline = DISABLED_FILL, DISABLED_LINE
            name_color = price_color = plus_color = DISABLED_TEXT

        self.round_rect(x, y, w, h, 12, fill, outline, shadow=enabled)
        self.text(x + 24, y + 12, coffee.name, 15, name_color)
        self.text(x + w - 62, y + 12, f'${coffee.price:.2f}', 15,
                  price_color, 'right', 'bold')

        # Plus icon
        self.disc(x + w - 28, cy, 12, plus_color)
        self.line([(x + w - 34, cy), (x + w - 22, cy)], WHITE, 3)
        self.line([(x + w - 28, cy - 6), (x + w - 28, cy + 6)], WHITE, 3)

        if enabled:
            self.buttons.append((x, y, w, h, lambda c=coffee: self.add(c)))

    # Draw the order summary panel
    def draw_order_panel(self):
        self.round_rect(-240, -285, 480, 173, 16, CARD, BORDER, shadow=True)

        count = len(self.order.items)
        self.text(-215, -137, 'Your Order', 15, TEXT, 'left', 'bold')
        self.text(215, -135, f'{count} item{"s" if count != 1 else ""}',
                  11, MUTED, 'right', 'italic')
        self.line([(-215, -147), (215, -147)], BORDER, 1)

        groups = self.order.grouped()
        if not groups:
            self.text(0, -202, 'Your cup is empty - pick a coffee above',
                      12, MUTED, 'center', 'italic')
        else:
            y = -168
            can_remove = self.state == 'menu'
            for name, (qty, price) in groups.items():
                self.text(-215, y, f'{qty} x {name}', 13, TEXT)
                self.text(160, y, f'${qty * price:.2f}', 13, ACCENT, 'right', 'bold')

                # Remove-one button
                if can_remove:
                    cx, cy = 205, y + 8
                    self.disc(cx, cy, 11, SOFT, BORDER)
                    self.line([(cx - 5, cy), (cx + 5, cy)], TEXT, 3)
                    self.buttons.append(
                        (cx - 12, cy - 12, 24, 24,
                         lambda n=name: self.remove_one(n))
                    )
                y -= 23

        self.line([(-215, -252), (215, -252)], BORDER, 1)
        self.text(-215, -276, 'Total', 14, MUTED)
        self.text(215, -278, f'${self.order.total():.2f}', 18, TEXT, 'right', 'bold')

    # Draw the "order confirmed" message card on top of everything
    def draw_confirmation(self):
        self.buttons = []  # Only the card's button can be clicked now

        self.round_rect(-200, -70, 400, 210, 20, CARD, ACCENT, shadow=True)

        # Check mark
        self.disc(0, 100, 26, ACCENT)
        self.line([(-11, 100), (-3, 91), (12, 110)], WHITE, 4)

        self.text(0, 50, 'Order Confirmed!', 20, TEXT, 'center', 'bold')
        self.text(0, 25, 'Thank you! Your coffee is on its way.',
                  12, MUTED, 'center', 'italic')
        self.text(
            0, 0,
            f'{self.last_count} item{"s" if self.last_count != 1 else ""}'
            f'  -  Total: ${self.last_total:.2f}',
            13, TEXT, 'center', 'bold'
        )
        self.action_button(-90, -55, 180, 36, 'New Order',
                           self.new_order, primary=True)

    # Redraw all changing parts of the window
    def render(self):
        self.pen = self.dynamic_pen
        self.pen.clear()
        self.buttons = []

        for i, coffee in enumerate(self.menu):
            self.menu_button(i, coffee)

        has_items = bool(self.order.items)

        if self.state == 'confirm':
            self.action_button(-240, -104, 232, 36, 'Confirm',
                               self.confirm, primary=True)
            self.action_button(8, -104, 232, 36, 'Cancel', self.cancel)
        else:
            self.action_button(-240, -104, 150, 36, 'Checkout',
                               self.start_checkout, has_items, primary=True)
            self.action_button(-75, -104, 150, 36, 'Clear Order',
                               self.clear_order, has_items)
            self.action_button(90, -104, 150, 36, 'Exit', self.exit_app)

        self.draw_order_panel()
        self.text(0, -309, self.message, 11, MUTED, 'center', 'italic')

        if self.state == 'done':
            self.draw_confirmation()

        self.screen.update()

    # ---------- Click handling ----------

    # Find which button was clicked
    def on_click(self, x, y):
        for bx, by, w, h, callback in self.buttons:
            if bx <= x <= bx + w and by <= y <= by + h:
                callback()
                return

    # Add coffee to order
    def add(self, coffee):
        self.order.add_item(coffee)
        self.message = f'Added {coffee.name} to your order'
        self.render()

    # Remove one of an item from the order
    def remove_one(self, name):
        self.order.remove_one(name)
        self.message = f'Removed one {name}'
        self.render()

    # Ask the customer to confirm
    def start_checkout(self):
        self.state = 'confirm'
        self.message = f'Proceed to checkout? Total: ${self.order.total():.2f}'
        self.render()

    # Finish the order and show the thank-you message
    def confirm(self):
        self.last_total = self.order.total()
        self.last_count = len(self.order.items)
        self.order.clear()
        self.state = 'done'
        self.message = 'Order confirmed! Thank you!'
        self.render()

    # Go back to the menu
    def cancel(self):
        self.state = 'menu'
        self.message = 'Checkout cancelled'
        self.render()

    # Start a fresh order
    def new_order(self):
        self.state = 'menu'
        self.message = DEFAULT_MESSAGE
        self.render()

    # Remove everything from the order
    def clear_order(self):
        self.order.clear()
        self.message = 'Order cleared'
        self.render()

    # Close the window
    def exit_app(self):
        try:
            self.screen.bye()
        except (turtle.Terminator, tk.TclError):
            pass

    # Keep the window open and listen for clicks
    def run(self):
        try:
            self.screen.mainloop()
        except (turtle.Terminator, tk.TclError):
            pass


# Create the menu and start the app
def main():
    menu = [
        Coffee('Espresso', 2.5),
        Coffee('Latte', 3.5),
        Coffee('Cappuccino', 3.0),
        Coffee('Americano', 2.0)
    ]

    app = CoffeeApp(menu)
    app.run()


if __name__ == '__main__':
    main()
