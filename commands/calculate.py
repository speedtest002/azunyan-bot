from discord.ext import commands
from discord import app_commands
import math

class Calculate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="calculate", aliases=["cal","c","tinh"])
    @app_commands.describe(
        expression="Nhập phép tính (VD: 1+1, sqrt(16)...)",
        precision="Số chữ số thập phân (Chỉ chỉnh được ở Slash Command)"
    )
    async def calculate(self, ctx,*, expression: str, precision: int = 4):
        """
        Các phép tính cơ bản (hỗ trợ + - * / ** sqrt log sin cos tan ...)
        """
        def safe_eval(expr):
            expr = expr.replace("^", "**")  # Chuyển ^ thành lũy thừa
            expr = expr.replace("x", "*").replace("÷", "/").replace("π", "pi").replace("\*","*")  
            expr = expr.replace(",",".")

            allowed_names = {
                # Toán học cơ bản
                "sqrt": math.sqrt,
                "pow": pow,
                "abs": abs,
                "round": round,
                "log": math.log,
                "pi": math.pi,
                "e": math.e,
                "mod": lambda x, y: x % y, 

                # Lượng giác (radian)
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,

                # Lượng giác (độ)
                "sind": lambda x: math.sin(math.radians(x)),
                "cosd": lambda x: math.cos(math.radians(x)),
                "tand": lambda x: math.tan(math.radians(x)),
            }

            try:
                result = eval(expr, {"__builtins__": {}}, allowed_names)
                return result
            except Exception as e:
                return f"Lỗi: {e}"


        result = safe_eval(expression)
        if isinstance(result, (int, float)):
            result_str = f"{round(result, precision)}"
        else:
            result_str = result
        safe_expr = expression.replace("*", "\\*")

        if ctx.interaction:
            # Là slash command
            await ctx.send(f"{safe_expr} = {result_str}")
        else:
            # Là prefix command
            await ctx.send(f"Kết quả: {result_str}")

async def setup(bot):
    await bot.add_cog(Calculate(bot))
