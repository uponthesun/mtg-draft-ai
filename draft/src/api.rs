#[derive(Debug)]
#[derive(Clone)]
pub struct Card {
    pub name: String,
}

impl Card {
    pub fn new(name: &String) -> Self {
        Self {
           name: name.to_string(),
        }
    }
}

pub trait Drafter {
    fn pick(&self, pack: &Vec<Card>, owned_cards: &Vec<Card>, draft_info: &DraftInfo) -> u32;
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

