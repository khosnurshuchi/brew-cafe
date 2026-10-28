import json
import math
import os
import textwrap
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
STAR = '#d4a017'
STAR_EMPTY = '#e6dac0'
WHITE = '#ffffff'

WIDTH, HEIGHT = 600, 640
DEFAULT_MESSAGE = 'Tap a drink to add it to your order'
VISIBLE_ROWS = 4

# Menu sections
CATEGORIES = ['Coffee', 'Tea', 'Other Drinks']
TEMPS = ['Hot', 'Cold']

# Size and extras: (name, price change in Tk)
SIZES = [('Small', -20), ('Medium', 0), ('Large', 40)]
EXTRAS_BY_CATEGORY = {
    'Coffee': [('Extra shot', 40), ('Oat milk', 50), ('Vanilla', 30)],
    'Tea': [('Honey', 20), ('Lemon', 15), ('Ginger', 15)],
    'Other Drinks': [('Whipped cream', 30), ('Caramel', 25), ('Honey', 20)],
}
SIZE_PRICES = dict(SIZES)

# Saved data lives next to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, 'orders.json')
REVIEWS_FILE = os.path.join(BASE_DIR, 'reviews.json')


# Format a price in Bangladeshi Taka
def money(amount):
    return f'Tk {amount:,.0f}'


# Cut long text so it fits on one line
def shorten(text, limit):
    return text if len(text) <= limit else text[:limit - 3] + '...'


class Coffee:
    # A drink on the menu (the name "Coffee" is kept for every drink type)
    def __init__(self, name, price, category='Coffee', temp='Hot'):
        self.name = name
        self.price = price
        self.category = category
        self.temp = temp


class OrderItem:
    # One drink with its chosen size and extras
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
        extra_prices = dict(EXTRAS_BY_CATEGORY[self.coffee.category])
        return (self.coffee.price
                + SIZE_PRICES[self.size]
                + sum(extra_prices[e] for e in self.extras))

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
        # 'menu', 'options', 'confirm', 'done', 'history',
        # 'reviews' or 'write_review'
        self.state = 'menu'
        self.message = DEFAULT_MESSAGE
        self.buttons = []  # (x, y, w, h, callback)

        # Menu filters
        self.category = CATEGORIES[0]
        self.temp = TEMPS[0]

        self.history = self.load_json(HISTORY_FILE)
        self.reviews = self.load_json(REVIEWS_FILE)
        self.cart_scroll = 0
        self.last_total = 0
        self.last_count = 0
        self.last_order_no = 0

        # Current selection in the options card
        self.sel_coffee = None
        self.sel_size = 'Medium'
        self.sel_extras = []

        # Review being written
        self.rv_rating = 0
        self.rv_name = ''
        self.rv_comment = ''

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

    # Load a list from a JSON file
    def load_json(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    # Save a list to a JSON file
    def save_json(self, path, data):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
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

    # Draw a five-point star
    def star(self, cx, cy, r, filled):
        points = []
        for i in range(10):
            radius = r if i % 2 == 0 else r * 0.45
            angle = math.radians(90 + i * 36)
            points.append((cx + radius * math.cos(angle),
                           cy + radius * math.sin(angle)))
        self.polygon(points, STAR if filled else STAR_EMPTY)

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

    # Draw shop name and tagline (cup on the left)
    def draw_title(self):
        self.text(-112, 272, 'BREW CAFE', 26, TEXT, 'left', 'bold')
        self.text(-112, 248, 'Freshly brewed, always', 11, MUTED, 'left', 'italic')

    # Draw a simple coffee cup with saucer, handle and steam
    def draw_cup(self):
        s = 0.36            # Scale
        ox, oy = -185, 241  # Position

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
        pen.pensize(5)
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
            pen.pensize(2)
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

    # Draw the Coffee / Tea / Other and Hot / Cold tabs
    def draw_tabs(self):
        enabled = self.state == 'menu'

        for i, name in enumerate(CATEGORIES):
            self.action_button(
                -240 + i * 165, 208, 150, 32, name,
                lambda n=name: self.set_category(n),
                enabled, primary=(self.category == name), size=13
            )

        for i, name in enumerate(TEMPS):
            self.action_button(
                -240 + i * 248, 168, 232, 30, name,
                lambda n=name: self.set_temp(n),
                enabled, primary=(self.temp == name), size=13
            )

    # Draw a clickable menu item
    def menu_button(self, index, coffee):
        w, h = 480, 46
        x = -240
        y = 112 - index * 56
        cy = y + h / 2
        enabled = self.state == 'menu'

        if enabled:
            fill, outline = CARD, BORDER
            name_color, price_color, plus_color = TEXT, ACCENT, ACCENT
        else:
            fill, outline = DISABLED_FILL, DISABLED_LINE
            name_color = price_color = plus_color = DISABLED_TEXT

        self.round_rect(x, y, w, h, 12, fill, outline, shadow=enabled)
        self.text(x + 24, y + 15, coffee.name, 15, name_color)
        self.text(x + w - 62, y + 15, money(coffee.price), 15,
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
            self.text(0, -202, 'Your cup is empty - pick a drink above',
                      12, MUTED, 'center', 'italic')
        else:
            y = -168
            visible = rows[self.cart_scroll:self.cart_scroll + VISIBLE_ROWS]
            for key, (qty, unit, item) in visible:
                self.text(-215, y, shorten(f'{qty} x {item.label}', 38),
                          12, TEXT)
                self.text(160, y, money(qty * unit), 13, ACCENT, 'right', 'bold')

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
        self.text(215, -278, money(self.order.total()), 18, TEXT, 'right', 'bold')

    # Draw a big centered card on top of the menu
    def draw_card(self):
        self.buttons = []  # Only the card's buttons can be clicked now
        self.round_rect(-220, -110, 440, 290, 20, CARD, ACCENT, shadow=True)

    # Card where the customer picks size and extras
    def draw_options(self):
        self.draw_card()
        item = OrderItem(self.sel_coffee, self.sel_size, self.sel_extras)

        self.text(0, 150, f'{self.sel_coffee.name}  -  {money(self.sel_coffee.price)}',
                  18, TEXT, 'center', 'bold')

        # Size buttons
        self.text(-202, 112, 'Size', 12, MUTED, 'left', 'bold')
        for i, (name, delta) in enumerate(SIZES):
            label = name
            if delta:
                sign = '+' if delta > 0 else '-'
                label += f' {sign}Tk {abs(delta)}'
            self.action_button(
                -202 + i * 138, 68, 128, 34, label,
                lambda n=name: self.set_size(n),
                primary=(self.sel_size == name), size=12
            )

        # Extras buttons (can pick any number)
        self.text(-202, 40, 'Extras', 12, MUTED, 'left', 'bold')
        extras = EXTRAS_BY_CATEGORY[self.sel_coffee.category]
        for i, (name, price) in enumerate(extras):
            self.action_button(
                -202 + i * 138, -8, 128, 40, name,
                lambda n=name: self.toggle_extra(n),
                primary=(name in self.sel_extras), size=12,
                sublabel=f'+Tk {price}'
            )

        self.text(0, -34, f'Price: {money(item.price)}', 15, ACCENT, 'center', 'bold')

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
        self.text(0, 25, f'Order #{self.last_order_no} - your order is on its way.',
                  12, MUTED, 'center', 'italic')
        self.text(
            0, 0,
            f'{self.last_count} item{"s" if self.last_count != 1 else ""}'
            f'  -  Total: {money(self.last_total)}',
            13, TEXT, 'center', 'bold'
        )
        self.action_button(-202, -70, 196, 36, 'New Order',
                           self.new_order, primary=True)
        self.action_button(6, -70, 196, 36, 'Leave a Review',
                           self.open_write_review)

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
                self.text(195, y, money(record.get('total', 0)),
                          12, ACCENT, 'right', 'bold')
                y -= 24

        self.line([(-195, 8), (195, 8)], BORDER, 1)

        # Sales today and best seller
        today = datetime.now().strftime('%Y-%m-%d')
        todays = [r for r in self.history if r.get('time', '').startswith(today)]
        sales = sum(r.get('total', 0) for r in todays)
        self.text(-195, -18, f'Sales today: {money(sales)}  ({len(todays)} orders)',
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

        self.action_button(-90, -95, 180, 36, 'Close', self.close_card,
                           primary=True)

    # Card showing customer reviews
    def draw_reviews(self):
        self.draw_card()
        self.text(0, 150, 'Customer Reviews', 18, TEXT, 'center', 'bold')

        if not self.reviews:
            self.text(0, 60, 'No reviews yet - be the first to share!',
                      12, MUTED, 'center', 'italic')
        else:
            # Average rating
            average = sum(r.get('rating', 0) for r in self.reviews) / len(self.reviews)
            for i in range(5):
                self.star((i - 2) * 26, 128, 9, i < round(average))
            total = len(self.reviews)
            self.text(0, 98,
                      f'{average:.1f} out of 5  -  {total} review{"s" if total != 1 else ""}',
                      12, MUTED, 'center')

            # Latest three reviews
            y = 74
            for review in reversed(self.reviews[-3:]):
                name = shorten(review.get('name') or 'Guest', 22)
                self.text(-195, y, name, 12, TEXT, 'left', 'bold')
                for i in range(5):
                    self.star(130 + i * 14, y + 6, 6, i < review.get('rating', 0))
                comment = review.get('comment', '')
                if comment:
                    self.text(-195, y - 17, shorten(comment, 58),
                              11, MUTED, 'left', 'italic')
                y -= 46

        self.action_button(-202, -92, 196, 36, 'Write a Review',
                           self.open_write_review, primary=True)
        self.action_button(6, -92, 196, 36, 'Close', self.close_card)

    # Card where the customer writes a review
    def draw_write_review(self):
        self.draw_card()
        self.text(0, 150, 'Write a Review', 18, TEXT, 'center', 'bold')

        # Star rating (click a star)
        self.text(-202, 120, 'Your rating', 12, MUTED, 'left', 'bold')
        for i in range(5):
            cx = (i - 2) * 52
            self.star(cx, 90, 17, i < self.rv_rating)
            self.buttons.append(
                (cx - 24, 66, 48, 48, lambda n=i + 1: self.set_rating(n))
            )

        # Name and comment (typed in a small pop-up box)
        self.action_button(-202, 34, 404, 30,
                           f'Name: {self.rv_name or "Guest"}  (tap to change)',
                           self.ask_name, size=12)
        self.action_button(-202, -4, 404, 30,
                           'Edit comment' if self.rv_comment else 'Write a comment',
                           self.ask_comment, size=12)

        # Comment preview
        if self.rv_comment:
            lines = textwrap.wrap(self.rv_comment, 56)
            shown = lines[:2]
            if len(lines) > 2:
                shown[1] = shorten(shown[1] + '...', 56)
            for i, line in enumerate(shown):
                self.text(-202, -23 - i * 14, line, 11, MUTED, 'left', 'italic')

        self.action_button(-202, -90, 196, 36, 'Submit', self.submit_review,
                           enabled=self.rv_rating > 0, primary=True)
        self.action_button(6, -90, 196, 36, 'Cancel', self.cancel_review)

    # Redraw all changing parts of the window
    def render(self):
        self.pen = self.dynamic_pen
        self.pen.clear()
        self.buttons = []

        # Reviews button in the top-right corner
        self.action_button(140, 258, 100, 34, 'Reviews', self.open_reviews,
                           self.state == 'menu', size=13)

        self.draw_tabs()

        visible = [c for c in self.menu
                   if c.category == self.category and c.temp == self.temp]
        for i, coffee in enumerate(visible[:4]):
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
        elif self.state == 'reviews':
            self.draw_reviews()
        elif self.state == 'write_review':
            self.draw_write_review()

        self.screen.update()

    # ---------- Click handling ----------

    # Find which button was clicked
    def on_click(self, x, y):
        for bx, by, w, h, callback in self.buttons:
            if bx <= x <= bx + w and by <= y <= by + h:
                callback()
                return

    # Switch between Coffee, Tea and Other Drinks
    def set_category(self, name):
        self.category = name
        self.render()

    # Switch between Hot and Cold
    def set_temp(self, name):
        self.temp = name
        self.render()

    # Open the size and extras card for a drink
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
            order = [n for n, _ in EXTRAS_BY_CATEGORY[self.sel_coffee.category]]
            self.sel_extras.sort(key=order.index)
        self.render()

    # Add the customized drink to the order
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
        self.message = f'Proceed to checkout? Total: {money(self.order.total())}'
        self.render()

    # Finish the order, save it and show the thank-you message
    def confirm(self):
        groups = self.order.grouped()
        order_no = max((r.get('id', 0) for r in self.history), default=0) + 1

        self.history.append({
            'id': order_no,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'count': len(self.order.items),
            'total': self.order.total(),
            'items': [
                {
                    'name': item.name,
                    'size': item.size,
                    'extras': list(item.extras),
                    'qty': qty,
                    'unit_price': unit,
                }
                for qty, unit, item in groups.values()
            ],
        })
        saved = self.save_json(HISTORY_FILE, self.history)

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

    # Close the history or reviews card
    def close_card(self):
        self.state = 'menu'
        self.message = DEFAULT_MESSAGE
        self.render()

    # ---------- Reviews ----------

    # Show customer reviews
    def open_reviews(self):
        self.state = 'reviews'
        self.message = 'What our customers say'
        self.render()

    # Start a new review
    def open_write_review(self):
        self.rv_rating = 0
        self.rv_name = ''
        self.rv_comment = ''
        self.state = 'write_review'
        self.message = 'Tap a star to rate us'
        self.render()

    # Set the star rating
    def set_rating(self, value):
        self.rv_rating = value
        self.render()

    # Ask for the customer's name in a pop-up box
    def ask_name(self):
        value = self.screen.textinput('Your name', 'Enter your name (optional):')
        if value is not None:
            self.rv_name = value.strip()[:24]
        self.render()

    # Ask for the comment in a pop-up box
    def ask_comment(self):
        value = self.screen.textinput('Your comment', 'Write your comment:')
        if value is not None:
            self.rv_comment = value.strip()[:200]
        self.render()

    # Save the review
    def submit_review(self):
        if self.rv_rating < 1:
            return

        self.reviews.append({
            'name': self.rv_name or 'Guest',
            'rating': self.rv_rating,
            'comment': self.rv_comment,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
        })
        saved = self.save_json(REVIEWS_FILE, self.reviews)

        self.state = 'reviews'
        self.message = ('Thank you for your review!' if saved
                        else 'Thanks! (review could not be saved)')
        self.render()

    # Leave without saving
    def cancel_review(self):
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


# Create the menu and start the app (prices are in Bangladeshi Taka)
def main():
    menu = [
        # Coffee - hot
        Coffee('Espresso', 120, 'Coffee', 'Hot'),
        Coffee('Latte', 180, 'Coffee', 'Hot'),
        Coffee('Cappuccino', 170, 'Coffee', 'Hot'),
        Coffee('Americano', 130, 'Coffee', 'Hot'),
        # Coffee - cold
        Coffee('Iced Latte', 200, 'Coffee', 'Cold'),
        Coffee('Iced Americano', 150, 'Coffee', 'Cold'),
        Coffee('Cold Brew', 220, 'Coffee', 'Cold'),
        Coffee('Coffee Frappe', 250, 'Coffee', 'Cold'),
        # Tea - hot
        Coffee('Milk Tea', 60, 'Tea', 'Hot'),
        Coffee('Black Tea', 40, 'Tea', 'Hot'),
        Coffee('Green Tea', 70, 'Tea', 'Hot'),
        Coffee('Masala Tea', 80, 'Tea', 'Hot'),
        # Tea - cold
        Coffee('Iced Lemon Tea', 90, 'Tea', 'Cold'),
        Coffee('Iced Peach Tea', 110, 'Tea', 'Cold'),
        Coffee('Mint Lemon Tea', 100, 'Tea', 'Cold'),
        Coffee('Iced Milk Tea', 100, 'Tea', 'Cold'),
        # Other drinks - hot
        Coffee('Hot Chocolate', 160, 'Other Drinks', 'Hot'),
        Coffee('Honey Ginger Lemon', 90, 'Other Drinks', 'Hot'),
        Coffee('Turmeric Milk', 100, 'Other Drinks', 'Hot'),
        Coffee('Hot Milk', 80, 'Other Drinks', 'Hot'),
        # Other drinks - cold
        Coffee('Mango Lassi', 150, 'Other Drinks', 'Cold'),
        Coffee('Fresh Lime Soda', 90, 'Other Drinks', 'Cold'),
        Coffee('Orange Juice', 140, 'Other Drinks', 'Cold'),
        Coffee('Chocolate Shake', 200, 'Other Drinks', 'Cold'),
    ]

    app = CoffeeApp(menu)
    app.run()


if __name__ == '__main__':
    main()
