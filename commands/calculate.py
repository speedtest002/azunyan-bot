from discord import *
from discord.ext import commands
import math
class Calculate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="calculate", aliases=["cal"])
    async def calculate(self,ctx):
        """
        Các phép tính cơ bản
        """

        def safe_eval(expression):
            # Define allowed functions and operators
            allowed_names = {
                "sqrt": math.sqrt,
                "pow": pow,
                "abs": abs,
                "round": round,
                "log": math.log,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "pi": math.pi,
                "e": math.e
            }

            try:
                # Evaluate the expression safely
                result = eval(expression, {"__builtins__": {}}, allowed_names)
                return result
            except Exception as e:
                return f"Error: {e}"
        await ctx.send(round(safe_eval(ctx.message.content.split(" ", 1)[1]),4))
async def setup(bot):
    await bot.add_cog(Calculate(bot))