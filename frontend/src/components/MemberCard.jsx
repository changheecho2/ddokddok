export default function MemberCard({ member }) {
  const { name, deposit_balance } = member

  const balanceColor =
    deposit_balance >= 40000
      ? 'text-green-600'
      : deposit_balance >= 20000
      ? 'text-yellow-600'
      : 'text-red-600'

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
      <p className="font-semibold text-gray-800">{name}</p>
      <p className={`text-sm mt-1 font-medium ${balanceColor}`}>
        {deposit_balance.toLocaleString()}원
      </p>
    </div>
  )
}
