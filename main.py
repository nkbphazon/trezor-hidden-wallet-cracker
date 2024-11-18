import time
import math
import itertools
from multiprocessing import Pool as ProcessPool
from multiprocessing import freeze_support
from signal import signal, SIGINT
from bip_utils import Bip39Mnemonic, Bip39SeedGenerator, Bip44Changes, Bip84, Bip84Coins

# how many parallel processes to launch
# leave as None to spawn one process per logical CPU core or override with a numeric value
POOL_SIZE = None

# potential known wallet addresses to try to match
WALLET_ADDRESSES = set([
    "bc1qddthiswillnotbefoundbecauseitisnotreal",
    "bc1qehae3svrdrm4j0wjv85vhshyt9lzv7xl579uws"
])

# the (zero-based) wallet address index - more than one wallet address can be derived from the same key
# the first number is the starting index, the second number is the stop index
# 0,1 - check the first wallet only (wallet 0)
# 0,2 - check the first two wallets (wallet 0-1)
# 0,5 - check the first five wallets (wallet 0-4)
WALLET_ADDRESS_INDICES = range(0,1)

# the seed phrase for the wallet
MNEMONIC = "scout employ license scrub skull cannon ability wink letter invest drip toy"

# the known prefix of the passphrase
PASSPHRASE_PREFIX = "testpassphrase1"

# how many additional characters to append from the character set
CHARACTERS_TO_APPEND = 4

# the set of characters to use when generated potential passphrases
CHARACTER_SET = list('abcdefghijklmnopqrstuvwxyz0123456789')

def interrrupt_handler(n, f):
    raise InterruptedError

def generate_wordlist(character_set, number_characters):
    return[x for x in itertools.product(*([character_set] * number_characters))]

def crack(addresses:set, passphrase:str, mnemonic: Bip39Mnemonic, address_numbers: range = range(0,1)):
    seed = Bip39SeedGenerator(mnemonic).Generate(passphrase=passphrase)
    master_key = Bip84.FromSeed(seed, Bip84Coins.BITCOIN)
    account_key = master_key.Purpose().Coin().Account(0)   # m/84'/0'/0'
    chain_key = account_key.Change(Bip44Changes.CHAIN_EXT) # m/84'/0'/0'/0

    for i in address_numbers:
        address_key = chain_key.AddressIndex(i)            # m/84'/0'/0'/0/i
        generated_address = address_key.PublicKey().ToAddress()
        if generated_address in addresses:
            print(f"Found passphrase '{passphrase}' for address {generated_address} on index {i}")
            return generated_address

def crack_multi(args):
    signal(SIGINT, interrrupt_handler)
    addresses, passphrase, mnemonic, address_numbers = args[0], args[1], args[2], args[3]
    crack(addresses=addresses, passphrase=passphrase, mnemonic=mnemonic, address_numbers=address_numbers)

def main():
    assert len(CHARACTER_SET) == len(set(CHARACTER_SET)), "character set contains duplicate values"
    passphrases = [f"{PASSPHRASE_PREFIX}{''.join(x)}" for x in generate_wordlist(CHARACTER_SET, CHARACTERS_TO_APPEND)]
    expected_passphrase_count = math.pow(len(CHARACTER_SET), CHARACTERS_TO_APPEND)
    assert len(set(passphrases)) == expected_passphrase_count, "duplicate words found in generated wordlist"

    passphrase_count = len(passphrases)
    total_comparison_count = len(WALLET_ADDRESS_INDICES) * passphrase_count

    print("Start cracking with the following parameters:")
    print(f"Process pool size: {POOL_SIZE}")
    print(f"Wallet address indices: {list(WALLET_ADDRESS_INDICES)}")
    print(f"Character set: {CHARACTER_SET}")
    print(f"Number of characters to append: {CHARACTERS_TO_APPEND}")
    print(f"Possible character combinations: {passphrase_count}")
    print(f"Total comparisons to make: {total_comparison_count} ({passphrase_count} passphrases * {len(WALLET_ADDRESS_INDICES)} wallets)\n")

    pool = ProcessPool(POOL_SIZE)
    start = time.time()
    pool.map(crack_multi, zip(itertools.repeat(WALLET_ADDRESSES), passphrases, itertools.repeat(MNEMONIC), itertools.repeat(WALLET_ADDRESS_INDICES)))
    pool.close()
    pool.join()

    end = time.time()
    duration = end-start
    print(f"Finished in {duration} seconds ({total_comparison_count/duration}/sec)")

if __name__ == '__main__':
    freeze_support()
    main()
