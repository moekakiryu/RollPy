"""
Useage: 
>>> Roll("2d4")
Roll(2d4): 8

>>> Roll("2d6+5") # more general useage
Roll(2d6+5): 11

>>> foo = Roll("2d6+5") # Roll object can be stored as a variable
>>> foo.roll() # to get a random roll from an object, use the roll method
9

>>> Roll("2d6*(5d4)") # functions like a normal calculator (dice rolls are calculated first)
Roll(2d6*(5d4)): 112

>>> Roll("[2+3*4]^4") # also doesn't need dice if you don't want it
Roll([2+3*4]^4): 38416

>>> Roll.d20(6) # roll a d20 with a +6 modifier (allows negative numbers)
15

>>> Roll.chacter_abilities() # get character stats
[10, 14, 17, 10, 13, 13]

>>> Roll.success_chance(15,6) # get the odds of passing a DC 15 check with a +6 modifier (may not be correct but meh)
0.6

"""
import string
import typing
import random
import math

class Roll:
    _operators = {"+":0,"-":0,"/":1,"*":1,"^":2}
    _brackets = {"(":")","[":"]","{":"}","<":">"}
    _plus = "+"
    _minus = "-"
    _mult = "*"
    _div = "/"
    _pow = "^"
    _dice_sep = 'd'
    
    def __init__(self,roll:str,adv=False,disadv=False):
        self.roll_str = roll
        self.adv = adv
        self.disadv = disadv

    def __repr__(self):
        return f"Roll({self.roll_str}): {self._eval_roll()}"

    def __str__(self):
        return self.__repr__()

    def __call__(self,adv=None,disadv=None):
        return self.roll(adv,disadv)

    @property
    def sdev(self):
        return math.sqrt(self._eval_roll(self._sdev_handler))

    @property
    def mean(self):
        return self._eval_roll(self._mean_handler)

    @property
    def max(self):
        return self._eval_roll(self._max_handler)

    @property
    def min(self):
        return self._eval_roll(self._min_handler)

    @staticmethod
    def _consume_number(infix_string:str,index:int,output:list) -> int:
        """consume a number token from infix_string starting at index and append result to output"""
        if not (infix_string[index].isdigit() or infix_string[index]==Roll._minus): # handle integers and dice rolls ('XdY')
            raise ValueError(f"Unexpected value in number token '{infix_string[index]}'")
        digit = ""
        has_mandatory_segment=False
        if infix_string[index]==Roll._minus:
            sign=1
            while index<len(infix_string) and infix_string[index]==Roll._minus:
                sign*=-1
                index+=1
            if sign<0:
                digit+=Roll._minus
        while index<len(infix_string) and infix_string[index].isdigit():
            has_mandatory_segment=True
            digit+=infix_string[index]
            index+=1
        if index<len(infix_string) and infix_string[index].lower()==Roll._dice_sep:
            digit+=infix_string[index].lower()
            index+=1
            has_mandatory_segment = False
            while index<len(infix_string) and infix_string[index].isdigit():
                has_mandatory_segment=True
                digit+=infix_string[index]
                index+=1
        if not has_mandatory_segment:
            raise ValueError("Dice rolls must be supplied with a fixed number of sides (format: 'XdY')")
        output.append(digit)
        return index

    @staticmethod
    def _push_operator(operator_stack:list,operator:str):
        output=None
        if (operator_stack and operator_stack[-1] not in Roll._brackets
           and Roll._operators[operator] <= Roll._operators[operator_stack[-1]]):
            output = operator_stack.pop()
        operator_stack.append(operator)
        return output

    @staticmethod
    def _infix_to_postfix_tokens(infix_string:str) -> typing.List[str]:
        output = []
        operator_stack = []
        i = 0
        while i<len(infix_string):
            if infix_string[i] in string.whitespace:
                if infix_string[i-1].isdigit() and i+1<len(infix_string) and infix_string[i+1].isdigit():
                    raise ValueError(f"Unexpected whitespace encountered at index {i}")
                i+=1
            elif infix_string[i] in Roll._brackets:
                operator_stack.append(infix_string[i])
                i+=1
            elif infix_string[i] in Roll._brackets.values(): # close brackets
                # get the key from Roll._brackets dict using the corresponding value
                open_bracket = next(filter(lambda k:Roll._brackets[k]==infix_string[i],Roll._brackets))
                while operator_stack and operator_stack[-1]!=open_bracket:
                    output.append(operator_stack.pop())
                # this operation checks for and removes the bracket itself ready for the
                # tokenizer to continue on
                if not (operator_stack and operator_stack.pop()==open_bracket):
                    raise ValueError(f"Unexpected '{infix_string[i]}' at index {i}: No matching opening '{open_bracket}'")
                i+=1
            elif infix_string[i] in Roll._operators:
                if i+1>=len(infix_string):
                    raise ValueError("Unexpected end of expression encountered (hanging operator)")
                top_operator = Roll._push_operator(operator_stack,infix_string[i])
                if top_operator:
                    output.append(top_operator)
                i+=1
                # (below) move ahead to check for negative number. If found, consume it
                while i<len(infix_string) and infix_string[i] in string.whitespace:
                    i+=1
                if infix_string[i]==Roll._minus:
                    i = Roll._consume_number(infix_string,i,output)
            elif infix_string[i].isdigit(): # handle integers and dice rolls ('XdY')
                i = Roll._consume_number(infix_string,i,output)
            else:
                raise ValueError(f"Unexpected character at index {i}: '{infix_string[i]}'")
        operator_stack.reverse()
        for operator in operator_stack:
            if operator in Roll._brackets:
                raise ValueError(f"Unbalanced brackets, '{operator}' was not closed")
            output.append(operator)
        return output

    @staticmethod
    def success_chance(dc,modifier=0,adv=False,disadv=False):
        """Get the probability that a d20 roll will beat a DC"""
        if adv:
            return 1-((dc-modifier-1)/20)**2
        elif disadv:
            return (1-(dc-modifier-1)/20)**2
        return 1-(dc-modifier-1)/20

    @classmethod
    def d20(self,modifier=0,adv=False,disadv=False):
        """Roll a d20"""
        return Roll(f"1d20+{modifier}")(adv,disadv)

    @classmethod
    def get_modifier(cls,n):
        return (n-10)//2

    @classmethod
    def chacter_abilities(cls,modifier_total_bounds=(-10,10),score_bounds=(1,20),pretty=False):
        scores = [0] # this will cause the loop to run at least once
        modifier_total = 0
        while (any(map(lambda s:s<score_bounds[0],scores))
               or any(map(lambda s:s>score_bounds[1],scores))
               or modifier_total<modifier_total_bounds[0]
               or modifier_total>modifier_total_bounds[1]):
            scores = [sum(sorted([Roll("1d6").roll() for r in range(4)])[1:]) for s in range(6)]
            modifier_total = sum(map(lambda s:cls.get_modifier(s),scores))
        return scores

    def _max_handler(self,sig:int,num:int,sides:typing.Union[int,None],adv=None,disadv=None)->int:
        if sig<0:
            return sig*num
        return sig*num*sides if sides else sig*num
    
    def _min_handler(self,sig:int,num:int,sides:typing.Union[int,None],adv=None,disadv=None)->int:
        if sig<0:
            return sig*num*sides if sides else sig*num
        return sig*num
        
    def _mean_handler(self,sig:int,num:int,sides:typing.Union[int,None],adv=None,disadv=None)->int:
        if sides:
            return sig*num*((sides+1)/2)
        return sig*num

    def _sdev_handler(self,sig:int,num:int,sides:typing.Union[int,None],adv=None,disadv=None)->int:
        if sides:
            return (num/12.0)*(sides**2-1)
        return 0

    def _get_one_roll(self,sides:int,adv=None,disadv=None):
        roll = random.randint(1,sides)
        if (self.adv and not self.disadv and adv==None and disadv==None) or (adv and not disadv):
            roll = max(roll,random.randint(1,sides))
        elif (self.disadv and not self.adv and adv==None and disadv==None) or (disadv and not adv):
            roll = min(roll,random.randint(1,sides))
        return roll

    def _roll_handler(self,sig:int,num:int,sides:typing.Union[int,None],adv=None,disadv=None)->int:
        sig = 1 if sig>0 else -1
        if sides:
            return sig*sum([self._get_one_roll(sides,adv,disadv) for i in range(num)])
        else:
            return sig*num

    def _eval_roll(self,handler=None,adv=None,disadv=None) -> float:
        if not handler:
            handler = self._roll_handler
        tokens = Roll._infix_to_postfix_tokens(self.roll_str)
        stack = []
        for token in tokens:
            if token in Roll._operators:
                b = stack.pop()
                a = stack.pop()
                if token == Roll._plus:
                    stack.append(a+b)
                elif token == Roll._minus:
                    stack.append(a-b)
                elif token == Roll._mult:
                    stack.append(a*b)
                elif token == Roll._div:
                    stack.append(a/b)
                elif token == Roll._pow:
                    stack.append(a**b)
            else:
                sig = 1
                if token.startswith('-'):
                    token = token.lstrip('-')
                    sig = -1
                if Roll._dice_sep in token:
                    num,sides = map(int,token.split(Roll._dice_sep,1))
                else:
                    num,sides = int(token),None
                handled = handler(sig,num,sides,adv,disadv)
                stack.append(handled)
        assert len(stack)==1
        return stack[0]
        
    def roll(self,adv=None,disadv=None):
        return self._eval_roll(adv,disadv)
