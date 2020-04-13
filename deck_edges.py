#!/usr/bin/env python
# coding: utf-8

# In[23]:
import sys

deck_file = sys.argv[1]

with open(deck_file, 'r') as f:
    lines = f.readlines()


# In[24]:


decklist = []
for line in lines:
    if 'CubeTutor.com' in line:
        continue
    if not line.strip():
        break
    
    # Example line:
    # 1 Cloudfin Raptor\n
    # Get remainder of string after first space, and trim ending newline
    card_name = line[line.index(' ')+1:].strip()
    
    decklist.append(card_name)


# In[25]:


from mtg_draft_ai.api import *

cards = read_cube_toml('cube_81183_tag_data.toml')
cards_by_name = {c.name: c for c in cards}


# In[28]:


from mtg_draft_ai import synergy

cards_in_deck = [cards_by_name[cn] for cn in decklist]
num_edges = len(synergy.create_graph(cards_in_deck).edges)


# In[29]:


print('Num edges: {}'.format(num_edges))


# In[ ]:




