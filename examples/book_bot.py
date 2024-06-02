from hulio import Component


class BookBot(Bot):
    token = '...'


class Book(BaseModel):
    id: str
    title: str
    image: str


class ChooseBook(TemplateMessageView, template='choose_book.xml'):
    """
    <message>
        <photo src.py="books[book_index].image"/>

        <section>
            <p> Книги: </p>
            <p for="i, book in enumerable(books)">
                <span if="i == book_index"> 📖 </span> <span else=""> 📘 </span>
                {book.title}
            </p>
        </section>

        <section>
            Введите часть названия книги, чтобы её выбрать.
        </section>

        <inline-keyboard>
            <button cd="{up}"> ^ </button>
            <button cd="{read}"> Читать </button>
            <button cd="{down}"> v </button>
        </inline-keyboard>
    </message>
    """

    books: list[Book]
    book_index: int = 0

    def __created__(self):
        self.books = database.fetch_books()

    @Button()
    async def read(self):
        book_id = self.books[self.book_index].id
        await BookReader(book_id=book_id).stack()

    @Button()
    async def up(self):
        self.book_index = min(self.book_index + 1, len(self.books))
        self.refresh()

    @Button()
    async def down(self):
        self.book_index = max(0, self.book_index - 1)
        self.refresh()

    @action.message
    async def search(self, message: Message):
        for i, book in self.books:
            if book.title.lower().startswith(message.text.lower()):
                self.book_index = i
                break
        self.refresh()


class BookReader(TemplateMessageView):
    book_id: str = Field()
    current_page: int = Field(init_var=False, default=0)
    total_pages: int = Field(init_var=False, default=0)

    def __created__(self, user: Optional[User]):
        if user is not None:
            self.current_page = database.get_page_for_user(
                book_id=self.book_id,
                user_id=user.id
            )

    @context(alias='page')
    def page(self):
        pass

    @button
    async def next(self):
        pass

    @button
    async def prev(self):
        pass


BookBot.run()
