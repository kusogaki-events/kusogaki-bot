from config import TOKEN
from kusogaki_bot.core.bot import KusogakiBot


def main():
    bot = KusogakiBot()
    bot.run(TOKEN)


if __name__ == '__main__':
    main()
