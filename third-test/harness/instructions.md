# Participant instructions

The English instructions from the authors' replication package (`source/zenodo/extracted/3-Replication-Package/Instructions/*-English.pdf`), with the corrections listed in APPROACH.md (Design, Instructions). The harness uses the text under each `## name` heading verbatim and fills `{placeholders}` in code. Reply formats are enforced by the model adapter, not by this text.

Every player gets `system`, then `opening` + the treatment's section + `closing` together with the first period. The opening is identical in all eight files except that SC/S-D, SC/A-D and CH/S-D write "9 periods" for "nine periods"; it is used once here, with words. `{tables}` are generated from the payoff formula (`game.tables_text`), which also corrects the one misprinted cell. The chat treatments' "time limit of two minutes" (45 seconds in EC-MC) is replaced by a turn limit and `chat_rules`. `block2` is shown before period 10 with the z-Tree block screen (`block_screen`).

Corrections by treatment, beyond typos: CH/S-D lets only F and C write and tells them A reads the chat (paper p. 1954); SC/S-D, SC/A-D and CH/S-D say the persons "will not change"; CH/A-D uses the delegation wording of CH/S-D for decisions, payoffs and feedback; the leftover "send their messages independently" sentence is gone from CH/A-D, CH-MC and EC-MC; EC-MC names player A as the sender of the first two messages.

## system

Act as player {role} in a paid decision-making study with three participants. Make the next message or decision for this player using only the study instructions, the information available to this player, and the interaction history.

## opening

Thanks for coming to the experiment. You will receive 5 euros for participation in the experiment. Also, you will earn additional money during the experiment.

Participants have been randomly assigned to one of three roles: F, C and A. This role will be the same throughout the experiment.

There will be 18 separate periods. We will now present the instructions for the first block of nine periods. Later you will receive further instructions. In each period, you will be in a group of three participants, one in each role. The composition of each group is randomly determined at the beginning of the nine periods and stays constant during the nine periods. During the nine periods you will be with the same two persons. Also, at no time will you know the identity of who you are matched with.

Each period is independent from the others and develops in the following way. At the beginning of the period, the computer will randomly determine which of the following five games will be played.

{tables}

In each of the cells the first number is the payoff that the person in the F role will receive, the second number is the payoff that the person in the C role will receive and the third number is the payoff for the person in the A role. As you can see all five games have five rows: f1, f2, f3, f4 and f5, and five columns; c1, c2, c3, c4 and c5. Observe also that the numbers in the different cells differ between the games.

Each of the five games has the same chance of being chosen in each period separately. That is in each period, each of the games will be chosen with 20% probability. Player F and player C will be informed of which game has been chosen, but player A will not be informed of which game has been chosen.

## NC-D

After having seen which game has been selected by the random draw, players F and player C will separately make decisions. Player F will choose between f1, f2, f3, f4 and f5 and player C will choose between columns c1, c2, c3, c4 and c5. Player A will not make any decisions.

The payoffs of players F, C and A will be the ones in the cell determined by the row chosen by F and the column chosen by C for the game selected by the random draw. Remember that players F and C will make their decisions independently from each other.

After each period everybody will be informed about what row was chosen by F and what column was chosen by C and about which game was randomly selected.

## SC/S-D

Before making their decisions in each period the F and the C player will both have the opportunity to suggest a choice of a row and of a column to the other player. They will be able to do this three times in each period. After both players will have suggested choices of row and column a first time, both players will see the suggestion of the other player. Then they will be able to make suggestions a second time. This suggestion may or may not be different from the one made the first time. After both players will have made a suggestion a second time, both players will see the new suggestion of the other player. Then they will be able to make a suggestion a third time. This suggestion may or may not be different from the previous suggestions.

After having seen the third suggestion players F and player C will separately make decisions. The suggestions of the other player may or may not be followed. Player F will choose between f1, f2, f3, f4 and f5 and player C will choose between columns c1, c2, c3, c4 and c5. Player A will not make any decisions.

The payoffs of players F, C and A will be the ones in the cell determined by the row chosen by F and the column chosen by C for the game selected by the random draw. Remember that players F and C will make their decisions independently from each other.

After each period everybody will be informed about what row was chosen by F and what column was chosen by C and about which game was randomly selected.

## SC/A-D

Before the F and the C player make their decisions in each period the A player will have the opportunity to suggest to the F and the C players a choice of a row and a choice of a column. The A player will make a suggestion of row and column for each of the five possible games that may have been randomly selected. These suggestions may or may not be the same for the different games.

After having seen the suggestions of the A player, players F and player C will separately make decisions. The suggestion of the A player may or may not be followed. Player F will choose between f1, f2, f3, f4 and f5 and player C will choose between columns c1, c2, c3, c4 and c5. Player A will not make any decisions.

The payoffs of players F, C and A will be the ones in the cell determined by the row chosen by F and the column chosen by C for the game selected by the random draw. Remember that players F and C will make their decisions independently from each other.

After each period everybody will be informed about what row was chosen by F and what column was chosen by C and about which game was randomly selected.

## SC-MC

After having seen which game has been selected by the random draw, players F and player C will separately send messages to player A saying which game has been selected. This message can be truthful or not. Once player A has received the messages he will choose a row and column without knowing which game was selected.

The payoffs of players F, C and A will be the ones in the cell determined by the row and the column chosen by A for the game selected by the random draw. Remember that players F and C will send their messages independently from each other.

After each period everybody will be informed about what row and what column was chosen by A and about which game was randomly selected.

## CH/S-D

Before making their decisions in each round, players F and C have the opportunity to communicate through a chat with a limit of {turns} turns per period. Player A can read the chat but cannot write in it. {chat_rules}

Once the chat has finished player F will choose between f1, f2, f3, f4 and f5 and player C will choose between c1, c2, c3, c4 and c5. Player A will not make any decision.

The payoffs of players F, C and A will be the ones in the cell determined by the row chosen by F and the column chosen by C for the game selected by the random draw. Remember that players F and C will make their decisions independently from each other.

After each period everybody will be informed about what row was chosen by F and what column was chosen by C and about which game was randomly selected.

## CH/A-D

Before making decisions, players A, C and F have the opportunity to communicate through a chat with a limit of {turns} turns per period. {chat_rules}

Once the chat has finished player F will choose between f1, f2, f3, f4 and f5 and player C will choose between c1, c2, c3, c4 and c5. Player A will not make any decision.

The payoffs of players F, C and A will be the ones in the cell determined by the row chosen by F and the column chosen by C for the game selected by the random draw. Remember that players F and C will make their decisions independently from each other.

After each period everybody will be informed about what row was chosen by F and what column was chosen by C and about which game was randomly selected.

## CH-MC

Before making decisions, players A, C and F have the opportunity to communicate through a chat with a limit of {turns} turns per period. {chat_rules}

Once the chat has finished, player A will choose a row and a column without knowing which game has been selected.

The payoffs of players F, C and A will be the ones in the cell determined by the row and the column chosen by A for the game selected by the random draw.

After each period everybody will be informed about what row and what column was chosen by A and about which game was randomly selected.

## EC-MC

Before making decisions, players A, C and F have the opportunity to communicate through a chat with a limit of {turns} turns per period. In the chat the messages that can be sent are fixed. Player A will be able to send the messages 'What game is it?' and 'Please, tell me the truth' or not send any message. Player F can send the messages 'It is game ___', 'I am telling the truth', 'C is telling the truth', 'C is lying' or not send any message. Player C can send the messages 'It is game ___', 'I am telling the truth', 'F is telling the truth', 'F is lying' or not send any message. You can send one message in each turn, including repeated messages. {chat_rules}

Once the chat has finished, player A will choose a row and a column without knowing which game has been selected.

The payoffs of players F, C and A will be the ones in the cell determined by the row and the column chosen by A for the game selected by the random draw.

After each period everybody will be informed about what row and what column was chosen by A and about which game was randomly selected.

## chat_rules

The chat runs in turns. In each turn, every player who can write in the chat has one opportunity, in a random order, to write one message or to stay silent, and sees all messages written before. The chat ends after {turns} turns, or earlier after a turn in which nobody writes.

## closing

After this, a new period will start which will develop in the same way until reaching period 9. Remember that the persons you play with will not change from period to period.

Each ECU is worth 0,02 euros. At the end of the session you will receive 5 euros plus what you will have earned in all 18 rounds of the experiment.

You can ask questions at any time. If you have a question, please raise your hand and one of us will come to your place to answer it.

## block_screen

Block 2. There will now be another 9 periods with the same conditions as before. In each period you will play with the same people. The rules will not change for the second block of nine periods. The persons you play with are the same as in the first nine periods.

## header_informed

Block {block}, period {period} of 9. The computer selected Game {game}. Player A does not know which game was selected.

## header_uninformed

Block {block}, period {period} of 9. You do not know which game was selected.

## result

Result of block {block}, period {period}: the game was Game {game}. {choices} Payoffs this period: F {pay_f}, C {pay_c}, A {pay_a} ECU.

## ask_row

Choose a row (f1 to f5).

## ask_column

Choose a column (c1 to c5).

## ask_cell

Choose a row (f1 to f5) and a column (c1 to c5).

## ask_suggestion

Suggestion {k} of 3: suggest a row and a column.

## ask_advice

Suggest a row and a column for each of the five games.

## ask_report

Send player A a message saying which game has been selected.

## ask_chat

Chat, turn {turn} of {turns}. Messages this period:
{transcript}

Write one brief, complete message, or stay silent (null).

## ask_preset

Chat, turn {turn} of {turns}. Messages this period:
{transcript}

Choose one of your messages, or send no message (null).

## chat_ended

The chat has ended. Messages this period:
{transcript}

## note

Also add a one-sentence private note on why. Other participants never see your notes.

## retry

Your previous reply could not be used ({error}). Reply again in the required format.
