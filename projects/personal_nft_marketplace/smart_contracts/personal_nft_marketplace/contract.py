from algopy import ARC4Contract, Asset, Bytes, Global, String, Txn, UInt64, arc4, gtxn, itxn, op, subroutine
from algopy.arc4 import abimethod

class PurchaseEvent(arc4.Struct):
    asset_id: arc4.UInt64
    listed_price: arc4.UInt64
    buyer: arc4.Address
    processed_timestamp: arc4.UInt64


class PersonalNftMarketplace(ARC4Contract):
    @abimethod()
    def creator(self) -> arc4.Address:
        """
        Returns: the creator's address
        """
        return arc4.Address(Global.creator_address)

    @subroutine
    def creator_only(self) -> None:
        """
        only onwer can access this function
        """
        assert Txn.sender == Global.creator_address

    @abimethod()
    def opt_in(self, nft: Asset) -> None:
        """
        Opts the contract into an asset
        """
        self.creator_only() # only for creator
        itxn.AssetTransfer(
            xfer_asset=nft,
            asset_receiver=Global.current_application_address,
            asset_amount=0,
            fee=0
        ).submit()

    @abimethod
    def list_nft(self, axfer: gtxn.AssetTransferTransaction, price: arc4.UInt64) -> None:
        self.creator_only()
        assert axfer.asset_receiver == Global.current_application_address, "Receiver must be the application address"
        assert axfer.asset_amount == 1, "Asset amount must be 1"

        op.Box.put(self.box_key(axfer.xfer_asset), price.bytes)

    @subroutine
    def box_key(self, nft: Asset) -> Bytes:
        return op.itob(nft.id)

    @abimethod
    def get_price(self, nft: Asset) -> UInt64:
        # get info of asset into Box
        value, exists = op.Box.get(self.box_key(nft))
        assert exists, "Price not found"
        return op.btoi(value)

    @abimethod
    def purchase_nft(self, nft: Asset, payment: gtxn.PaymentTransaction) -> None:
        # Check
        assert nft.balance(Global.current_application_address), "NFT not available"
        assert payment.receiver == Global.creator_address, "Payment receiver must be creator address"
        assert payment.amount >= (self.get_price(nft)), "Payment amount must be larger than price"
        assert payment.sender.is_opted_in(nft), "Sender must opt in to receive NFT"

        itxn.AssetTransfer(
            xfer_asset=nft,
            asset_receiver=payment.sender,
            asset_amount=1,
            fee=0
        ).submit()

        arc4.emit(
            PurchaseEvent(
                arc4.UInt64(nft.id),
                arc4.UInt64(self.get_price(nft)),
                arc4.Address(payment.sender),
                arc4.UInt64(Global.latest_timestamp)
            )
        )

        _deleted = op.Box.delete(self.box_key(nft))
