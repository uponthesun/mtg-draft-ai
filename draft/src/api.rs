use std::fmt;

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
    pub num_drafters: usize,
    pub num_phases: usize,
    pub cards_per_pack: usize,
}

// Will probably refactor this so that each Drafter keeps track of owned cards,
// either through composition or an abstract base class, in the Python port.
pub struct DraftState {
    pub drafters: Vec<Box<Drafter>>,
    // The packs in a draft are organized into X phases of Y packs, each of which has Z cards.
    // E.g. a typical draft has 3 phases, 8 packs in each (one per drafter), and 15 cards per pack.
    // Likewise, the outermost Vec represents phase, the next nested Vec represents packs in a phase, and the
    // innermost Vec represents the cards in a single pack.
    pub packs: Vec<Vec<Vec<Card>>>,
    // The cards owned (previously picked) by each drafter so far. The outermost Vec represents
    // the drafters, and the inner Vec represents the collection of cards they've picked so far in the draft.
    pub owned_cards: Vec<Vec<Card>>,
}

impl DraftState {
    pub fn new(drafters: Vec<Box<Drafter>>, packs: Vec<Vec<Vec<Card>>>) -> Self {
        let mut owned_cards: Vec<Vec<Card>> = vec![];
        for _d in drafters.iter() {
            owned_cards.push(vec![]);
        }

        Self {
            drafters,
            packs,
            owned_cards
        }
    }
}

impl fmt::Debug for DraftState {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "DraftState {{ packs: {:?}, owned_cards: {:?} }}", self.packs, self.owned_cards)
    }
}