import json
import math
import os
import turtle
import tkinter as tk
from datetime import datetime

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
VISIBLE_ROWS = 4

# Size and extras: (name, price change)
SIZES = [('Small', -0.50), ('Medium', 0.0), ('Large', 0.75)]
EXTRAS = [('Extra shot', 0.50), ('Oat milk', 0.60), ('Vanilla', 0.40)]
SIZE_PRICES = dict(SIZES)
EXTRA_PRICES = dict(EXTRAS)
EXTRA_ORDER = [name for name, _ in EXTRAS]

# Order history is saved next to this script
HISTORY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'orders.json'
)


# Cut long text so it fits on one line
def shorten(text, limit):
    return text if len(text) <= limit else text[:limit - 3] + '...'


class Coffee:
    # Initialize coffee with name and price
    def __init__(self, name, price):
        self.name = name
        self.price = price


class OrderItem:
    # One coffee with its chosen size and extras
    def __init__(self, coffee, size='Medium', extras=()):
        self.coffee = coffee
        self.size = size
        self.extras = tuple(extras)

    @property
    def name(self):
        return self.coffee.name

    # Price including size and extras
    @property
    def price(self):
        return (self.coffee.price
                + SIZE_PRICES[self.size]
                + sum(EXTRA_PRICES[e] for e in self.extras))

    # Items with the same key are grouped together in the cart
    @property
    def key(self):
        return (self.name, self.size, self.extras)

    # Short description, e.g. "Latte (L) + Oat milk"
    @property
    def label(self):
        text = f'{self.name} ({self.size[0]})'
        if self.extras:
            text += ' + ' + ', '.join(self.extras)
        return text


class Order:
    # Initialize order with empty list
    def __init__(self):
        self.items = []

    # Add an item to the order
    def add_item(self, item):
        self.items.append(item)

    # Remove one item matching this key
    def remove_one(self, key):
        for i in range(len(self.items) - 1, -1, -1):
            if self.items[i].key == key:
                del self.items[i]
                return

    # Calculate total price
    def total(self):
        return sum(item.price for item in self.items)

    # Group identical items: {key: [count, unit_price, item]}
    def grouped(self):
        groups = {}
        for item in self.items:
            if item.key not in groups:
                groups[item.key] = [0, item.price, item]
            groups[item.key][0] += 1
        return groups

    # Remove everything from the order
    def clear(self):
        self.items.clear()


class CoffeeApp:
    # Build the window and draw everything
    def __init__(self, menu):
        self.menu = menu
        self.order = Order()
        # 'menu', 'options', 'confirm', 'done' or 'history'
        self.state = 'menu'
        self.message = DEFAULT_MESSAGE
        self.buttons = []  # (x, y, w, h, callback)

        self.history = self.load_history()
        self.cart_scroll = 0
        self.last_total = 0.0
        self.last_count = 0
        self.last_order_no = 0

        # Current selection in the options card
        self.sel_coffee = None
        self.sel_size = 'Medium'
        self.sel_extras = []

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

    # ---------- Saving and loading ----------

    # Load past orders from the JSON file
    def load_history(self):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    # Save all orders to the JSON file
    def save_history(self):
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2)
            return True
        except OSError:
            return False

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
                      enabled=True, primary=False, size=14, sublabel=None):
        if not enabled:
            fill, outline, color = DISABLED_FILL, DISABLED_LINE, DISABLED_TEXT
        elif primary:
            fill, outline, color = ACCENT, ACCENT, WHITE
        else:
            fill, outline, color = SOFT, BORDER, TEXT

        self.round_rect(x, y, w, h, 12, fill, outline, shadow=enabled)
        if sublabel:
            # Two lines: name on top, smaller text (e.g. price) below
            self.text(x + w / 2, y + h / 2 + 1, label, size,
                      color, 'center', 'bold')
            self.text(x + w / 2, y + h / 2 - 14, sublabel, size - 1,
                      color, 'center', 'normal')
        else:
            self.text(x + w / 2, y + h / 2 - size * 0.58, label, size,
                      color, 'center', 'bold')
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
            self.buttons.append(
                (x, y, w, h, lambda c=coffee: self.open_options(c))
            )

    # Draw the order summary panel
    def draw_order_panel(self):
        self.round_rect(-240, -285, 480, 173, 16, CARD, BORDER, shadow=True)

        count = len(self.order.items)
        self.text(-215, -137, 'Your Order', 15, TEXT, 'left', 'bold')
        self.text(215, -135, f'{count} item{"s" if count != 1 else ""}',
                  11, MUTED, 'right', 'italic')
        self.line([(-215, -147), (215, -147)], BORDER, 1)

        rows = list(self.order.grouped().items())
        can_edit = self.state == 'menu'

        # Keep the scroll position valid
        max_scroll = max(0, len(rows) - VISIBLE_ROWS)
        self.cart_scroll = min(max(self.cart_scroll, 0), max_scroll)

        # Scroll arrows when the cart has more rows than fit
        if max_scroll > 0 and can_edit:
            for cx, direction in ((100, 1), (126, -1)):
                cy = -131
                self.disc(cx, cy, 9, SOFT, BORDER)
                self.line(
                    [(cx - 4, cy - 2 * direction),
                     (cx, cy + 2 * direction),
                     (cx + 4, cy - 2 * direction)],
                    TEXT, 2
                )
                step = -1 if direction == 1 else 1
                self.buttons.append(
                    (cx - 10, cy - 10, 20, 20,
                     lambda s=step: self.scroll_cart(s))
                )

        if not rows:
            self.text(0, -202, 'Your cup is empty - pick a coffee above',
                      12, MUTED, 'center', 'italic')
        else:
            y = -168
            visible = rows[self.cart_scroll:self.cart_scroll + VISIBLE_ROWS]
            for key, (qty, unit, item) in visible:
                self.text(-215, y, shorten(f'{qty} x {item.label}', 40),
                          12, TEXT)
                self.text(160, y, f'${qty * unit:.2f}', 13, ACCENT, 'right', 'bold')

                # Remove-one button
                if can_edit:
                    cx, cy = 205, y + 8
                    self.disc(cx, cy, 11, SOFT, BORDER)
                    self.line([(cx - 5, cy), (cx + 5, cy)], TEXT, 3)
                    self.buttons.append(
                        (cx - 12, cy - 12, 24, 24,
                         lambda k=key: self.remove_one(k))
                    )
                y -= 23

        self.line([(-215, -252), (215, -252)], BORDER, 1)
        self.text(-215, -276, 'Total', 14, MUTED)
        self.text(215, -278, f'${self.order.total():.2f}', 18, TEXT, 'right', 'bold')

    # Draw a big centered card on top of the menu
    def draw_card(self):
        self.buttons = []  # Only the card's buttons can be clicked now
        self.round_rect(-220, -110, 440, 290, 20, CARD, ACCENT, shadow=True)

    # Card where the customer picks size and extras
    def draw_options(self):
        self.draw_card()
        item = OrderItem(self.sel_coffee, self.sel_size, self.sel_extras)

        self.text(0, 150, f'{self.sel_coffee.name}  -  ${self.sel_coffee.price:.2f}',
                  18, TEXT, 'center', 'bold')

        # Size buttons
        self.text(-202, 112, 'Size', 12, MUTED, 'left', 'bold')
        for i, (name, delta) in enumerate(SIZES):
            label = name
            if delta:
                sign = '+' if delta > 0 else '-'
                label += f' {sign}${abs(delta):.2f}'
            self.action_button(
                -202 + i * 138, 68, 128, 34, label,
                lambda n=name: self.set_size(n),
                primary=(self.sel_size == name), size=12
            )

        # Extras buttons (can pick any number)
        self.text(-202, 40, 'Extras', 12, MUTED, 'left', 'bold')
        for i, (name, price) in enumerate(EXTRAS):
            self.action_button(
                -202 + i * 138, -8, 128, 40, name,
                lambda n=name: self.toggle_extra(n),
                primary=(name in self.sel_extras), size=12,
                sublabel=f'+${price:.2f}'
            )

        self.text(0, -34, f'Price: ${item.price:.2f}', 15, ACCENT, 'center', 'bold')

        self.action_button(-202, -90, 196, 36, 'Add to Order',
                           self.add_to_order, primary=True)
        self.action_button(6, -90, 196, 36, 'Cancel', self.cancel_options)

    # Card shown after the order is confirmed
    def draw_confirmation(self):
        self.draw_card()

        # Check mark
        self.disc(0, 100, 26, ACCENT)
        self.line([(-11, 100), (-3, 91), (12, 110)], WHITE, 4)

        self.text(0, 50, 'Order Confirmed!', 20, TEXT, 'center', 'bold')
        self.text(0, 25, f'Order #{self.last_order_no} - your coffee is on its way.',
                  12, MUTED, 'center', 'italic')
        self.text(
            0, 0,
            f'{self.last_count} item{"s" if self.last_count != 1 else ""}'
            f'  -  Total: ${self.last_total:.2f}',
            13, TEXT, 'center', 'bold'
        )
        self.action_button(-90, -55, 180, 36, 'New Order',
                           self.new_order, primary=True)

    # Card listing recent orders and sales
    def draw_history(self):
        self.draw_card()
        self.text(0, 150, 'Order History', 18, TEXT, 'center', 'bold')

        if not self.history:
            self.text(0, 70, 'No orders yet', 13, MUTED, 'center', 'italic')
        else:
            y = 118
            for record in reversed(self.history[-5:]):
                count = record.get('count', 0)
                self.text(
                    -195, y,
                    f'#{record.get("id", "?")}   {record.get("time", "")[5:]}'
                    f'   {count} item{"s" if count != 1 else ""}',
                    12, TEXT
                )
                self.text(195, y, f'${record.get("total", 0):.2f}',
                          12, ACCENT, 'right', 'bold')
                y -= 24

        self.line([(-195, 8), (195, 8)], BORDER, 1)

        # Sales today and best seller
        today = datetime.now().strftime('%Y-%m-%d')
        todays = [r for r in self.history if r.get('time', '').startswith(today)]
        sales = sum(r.get('total', 0) for r in todays)
        self.text(-195, -18, f'Sales today: ${sales:.2f}  ({len(todays)} orders)',
                  13, TEXT, 'left', 'bold')

        counts = {}
        for record in self.history:
            for entry in record.get('items', []):
                name = entry.get('name', '?')
                counts[name] = counts.get(name, 0) + entry.get('qty', 0)
        if counts:
            best = max(counts, key=counts.get)
            self.text(-195, -42, f'Best seller: {best} ({counts[best]} sold)',
                      12, MUTED, 'left', 'italic')

        self.action_button(-90, -95, 180, 36, 'Close', self.close_history,
                           primary=True)

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
            self.action_button(-240, -104, 111, 36, 'Checkout',
                               self.start_checkout, has_items,
                               primary=True, size=13)
            self.action_button(-117, -104, 111, 36, 'Clear Order',
                               self.clear_order, has_items, size=13)
            self.action_button(6, -104, 111, 36, 'History',
                               self.open_history, size=13)
            self.action_button(129, -104, 111, 36, 'Exit',
                               self.exit_app, size=13)

        self.draw_order_panel()
        self.text(0, -309, self.message, 11, MUTED, 'center', 'italic')

        if self.state == 'options':
            self.draw_options()
        elif self.state == 'done':
            self.draw_confirmation()
        elif self.state == 'history':
            self.draw_history()

        self.screen.update()

    # ---------- Click handling ----------

    # Find which button was clicked
    def on_click(self, x, y):
        for bx, by, w, h, callback in self.buttons:
            if bx <= x <= bx + w and by <= y <= by + h:
                callback()
                return

    # Open the size and extras card for a coffee
    def open_options(self, coffee):
        self.sel_coffee = coffee
        self.sel_size = 'Medium'
        self.sel_extras = []
        self.state = 'options'
        self.message = f'Customize your {coffee.name}'
        self.render()

    # Choose a size
    def set_size(self, name):
        self.sel_size = name
        self.render()

    # Turn an extra on or off
    def toggle_extra(self, name):
        if name in self.sel_extras:
            self.sel_extras.remove(name)
        else:
            self.sel_extras.append(name)
            self.sel_extras.sort(key=EXTRA_ORDER.index)
        self.render()

    # Add the customized coffee to the order
    def add_to_order(self):
        item = OrderItem(self.sel_coffee, self.sel_size, self.sel_extras)
        self.order.add_item(item)
        self.state = 'menu'
        self.message = f'Added {item.label} to your order'
        self.render()

    # Close the options card without adding anything
    def cancel_options(self):
        self.state = 'menu'
        self.message = DEFAULT_MESSAGE
        self.render()

    # Remove one of an item from the order
    def remove_one(self, key):
        self.order.remove_one(key)
        self.message = 'Removed one item'
        self.render()

    # Scroll the order list up or down
    def scroll_cart(self, step):
        self.cart_scroll += step
        self.render()

    # Ask the customer to confirm
    def start_checkout(self):
        self.state = 'confirm'
        self.message = f'Proceed to checkout? Total: ${self.order.total():.2f}'
        self.render()

    # Finish the order, save it and show the thank-you message
    def confirm(self):
        groups = self.order.grouped()
        order_no = max((r.get('id', 0) for r in self.history), default=0) + 1

        self.history.append({
            'id': order_no,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'count': len(self.order.items),
            'total': round(self.order.total(), 2),
            'items': [
                {
                    'name': item.name,
                    'size': item.size,
                    'extras': list(item.extras),
                    'qty': qty,
                    'unit_price': round(unit, 2),
                }
                for qty, unit, item in groups.values()
            ],
        })
        saved = self.save_history()

        self.last_order_no = order_no
        self.last_total = self.order.total()
        self.last_count = len(self.order.items)
        self.order.clear()
        self.cart_scroll = 0
        self.state = 'done'
        self.message = ('Order confirmed! Thank you!' if saved
                        else 'Order confirmed (history could not be saved)')
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
        self.cart_scroll = 0
        self.message = 'Order cleared'
        self.render()

    # Show past orders
    def open_history(self):
        self.state = 'history'
        self.message = 'Order history'
        self.render()

    # Close the history card
    def close_history(self):
        self.state = 'menu'
        self.message = DEFAULT_MESSAGE
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
