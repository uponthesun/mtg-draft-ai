#[derive(Debug, Clone, Hash, Eq, PartialEq)]
pub struct Card {
    pub name: String,
    pub mana_cost: ManaCost,
}

impl Card {
    pub fn new(name: &str, mana_cost: ManaCost) -> Self {
        Self {
            name: name.to_string(),
            mana_cost,
        }
    }
}

#[derive(Debug, Clone, Copy, Hash, Eq, PartialEq)]
pub enum BasicMana{
    Red,
    Green,
    Blue,
    Black,
    White,
    // Can be fulfilled by any mana type including colorless.
    Generic,
    // Specifically requests colorless mana.
    Colorless
}

#[derive(Debug, Clone, Hash, Eq, PartialEq)]
pub enum Mana{
    XCost(String),
    Phyrexian(BasicMana),
    Split(BasicMana, BasicMana),
    Standard(BasicMana),
    NumGeneric(i16),
    // paid with either 1 of the given basic or 2 generic mana
    SplitGeneric(BasicMana)
}

#[derive(Debug, Clone, Hash, Eq, PartialEq)]
pub struct ManaCost {
    pub cost: Vec<Mana>,
}

// TODO: File parsing and test data for ManaCost.
impl ManaCost{
    // Temporary constructor for mana cost while we don't have data for mana costs.
    pub fn new_empty() -> Self{
        let v = Vec::new();
        Self {
            cost: v
        }
    }
    pub fn new(cost: Vec<Mana>) -> Self{
        Self{
            cost
        }
    }
}

impl ManaCost {
    fn converted_mana_cost(&self) -> i16{
        let mut total: i16 = 0;
        for symbol in 0..self.cost.len(){
            match &self.cost[symbol] {
                Mana::XCost(str) => break,
                Mana::Phyrexian(basic) => total += 1,
                Mana::Split(basic, other_basic) => total += 1,
                Mana::Standard(basic) => total += 1,
                Mana::NumGeneric(amt) => total+= amt,
                // This is certainly debatable...
                Mana::SplitGeneric(basic) => total += 1,
            }
        };
        total
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

