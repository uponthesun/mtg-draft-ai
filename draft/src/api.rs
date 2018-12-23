#[derive(Debug, Clone, Hash, Eq, PartialEq)]
pub struct Card {
    pub name: String,
}

impl Card {
    pub fn new(name: &str) -> Self {
        Self {
           name: name.to_string(),
        }
    }
}

pub trait Drafter {
    fn pick<'a>(&self, pack: &'a [Card], owned_cards: &[Card], draft_info: &DraftInfo) -> &'a Card;
}

// Information about the configuration of the draft that is available to all drafters
// TODO: add validation on having enough cards in card_list
#[derive(Debug)]
pub struct DraftInfo {
    pub card_list: Vec<Card>,
    pub num_drafters: u32,
    pub num_packs: u32,
    pub cards_per_pack: u32,
}

