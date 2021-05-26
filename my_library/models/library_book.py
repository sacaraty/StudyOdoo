from datetime import timedelta
from odoo import models, fields, api
from odoo.api import model
from odoo.exceptions import ValidationError
class LibraryBook(models.Model):
    _name = 'library.book'
    name = fields.Char('Title', required=True)
    date_release = fields.Date('Release Date')
    author_ids = fields.Many2many(
        'res.partner',
        string='Authors'
    )
    _description = "Library Book"
    _order = 'date_release desc, name'
    _rec_name="short_name"
    short_name = fields.Char('Short Title', required=True)
    note = fields.Text('Internal note')
    state = fields.Selection(
        [
            ('draft', 'Not Available'),
            ('available', 'Available'),
            ('borrowed', 'Borrowed'),
            ('lost', 'Lost')
        ], 'State', default="draft"
    )
    description = fields.Html('Description')
    cover = fields.Binary('Book Cover')
    out_of_print = fields.Boolean('Out of Print')
    date_updated = fields.Datetime('Last Updated')
    pages = fields.Integer('Number of Pages')
    cost_price = fields.Float('Book Cost', digits='Book Price')
    reader_rating = fields.Float(
        'Reader Average Rating',
        digits=(14,4), # Optional precision decimals,
    )
    currency_id = fields.Many2one('res.currency', string='Currency')
    retail_price = fields.Monetary(
        'Retail Price'
        # option: currency_field = currency_id
    )

    publisher_id = fields.Many2one(
        'res.partner',
        string='Publisher'
    )
    
    category_id = fields.Many2one('library.book.category')
    age_days = fields.Float(
        string='Days from release',
        compute='_compute_age',
        inverse='_inverse_age',
        search='_search_age',
        store=False,
        compute_sudo=True
    )
    _sql_constraints = [
        ('name_unique', 'UNIQUE (name)', 'Title must be unique'),
        ('positive_page', 'CHECK(pages>0)', 'No of pages must be positive')
    ]
    publisher_city = fields.Char('Publisher City', related='publisher_id.city', readonly=True)

    @api.constrains('date_release')
    def _check_release_date(self) :
        for record in self:
            if record.date_release and record.date_release > fields.Date.today():
                raise models.ValidationError('Release date can not be in the future')
    
    @api.depends('date_release')
    def _compute_age(self):
        today = fields.Date.today()
        for book in self:
            if book.date_release:
                delta = today - book.date_release
                book.age_days = delta.days
            else :
                book.age_days = 0

    def _inverse_age(self):
        today = fields.Date.today()
        for book in self.filtered('date_release'):
            d = today - timedelta(days=book.age_days)
            book.date_release = d

    def _search_age(self, operator, value):
        today = fields.Date.today()
        value_days = timedelta(days=value)
        value_date = today - value_days
        operator_map = {
            '>': '<', '>=': '<=',
            '<': '>', '<=': '>=',
        }
        new_op = operator_map.get(operator, operator)
        return [('date_release', new_op, value_date)]
    
    @api.model
    def _referencable_models(self):
        models = self.env['ir.model'].search([
            ('field_id.name', '=', 'message_ids')
        ])
        return [(x.model, x.name) for x in models]
    
    ref_doc_id = fields.Reference(
        selection = '_referencable_models',
        string = 'Referencable Document'
    )

    @api.model
    def is_allowed_transition(self, old_state, new_state):
        allowed = [
            ('draft', 'available'),
            ('available', 'borrowed'),
            ('borrowed', 'available'),
            ('available', 'lost'),
            ('borrowed', 'lost'), 
        ]
        return (old_state, new_state) in allowed

    def change_state(self, new_state):
        for book in self:
            if book.is_allowed_transition(book.state, new_state):
                book.state = new_state
            else:
                continue
    
    def make_available(self):
        self.change_state('avalaible')
    
    def make_borrowed(self):
        self.change_state('borrowed')
    
    def make_lost(self):
        self.change_state('lost')

class ResPartner(models.Model):
    _inherit = 'res.partner'
    published_book_ids = fields.One2many(
        'library.book',
        'publisher_id',
        string='Published Books'
    )

    authored_book_ids = fields.Many2many(
        'library.book',
        string='Authored Books',
        # relation='library_book_res_partner_rel' # optional
    )

    count_books = fields.Integer('Number of authored books', compute='_compute_count_books')

    @api.depends('authored_book_ids')
    def _compute_count_books(self):
        for record in self:
            record.count_books = len(record.authored_book_ids)


